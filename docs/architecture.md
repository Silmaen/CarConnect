# Architecture

## Vue d'ensemble

```
            QML (ui/qml)   ← affichage, aucun calcul
                 │  propriétés, signaux, slots
          Backend (ui/backend.py)   ← thread Qt ; écrit le CSV via Recorder
                 │  signaux Qt (entre threads)
          Session (session.py)      ← thread de travail
           │ lecture cyclique + file de tâches
    ObdClient (obd/)       UdsClient (uds/)
           └─────────┬─────────┘
                  Elm327 (elm327/)    ← commandes AT, lignes de réponse
                     │
                Transport (transport/)  ← octets : BLE, RFCOMM, série, simulateur
```

Chaque couche ne connaît que celle du dessous. Tout ce qui est sous `ui/` est du Python pur, testable sans Qt ni
matériel.

## Threads

- **Thread Qt** : l'interface et le `Backend`. Il ne fait jamais d'entrée-sortie sur l'adaptateur.
- **Thread de session** (`Session`) : ouvre le transport, initialise l'adaptateur, puis boucle : exécuter les tâches en
  attente, lire les PIDs, publier un échantillon, attendre 50 ms.
- **Thread de recherche** : un thread jetable pour le scan BLE (5 s).
- **Boucle asyncio du BLE** : `BleTransport` fait tourner `bleak` (asynchrone) dans son propre thread et expose une
  interface synchrone.

Les rappels de `Session` s'exécutent dans le thread de session. Le `Backend` les convertit en **signaux Qt internes**
(préfixés `_`), que Qt livre dans le thread de l'interface. Les propriétés QML ne sont donc modifiées que dans le
thread Qt.

**Pourquoi une file de tâches** : un seul canal vers l'adaptateur, et chaque requête attend sa réponse. Les lectures
ponctuelles (défauts, bilan, calculateurs) sont soumises avec `Session.submit` et exécutées **entre deux cycles de
lecture**, jamais en même temps.

**Erreurs** : une exception dans la boucle de session ferme la connexion et remonte « Erreur : … », avec sa trace
dans le terminal. Deux erreurs de bus consécutives (`CAN ERROR`, `BUFFER FULL`…) sont tolérées : la session remet
l'adaptateur en configuration OBD-II et réessaie ; la troisième ferme la connexion. Un `Elm327Timeout` ferme la connexion
immédiatement. Une exception dans une tâche ponctuelle est interceptée par `Backend._submit` : elle s'affiche sans couper
la connexion.

**Journal** : avec la variable d'environnement `CARCONNECT_TRACE`, le `Backend` enveloppe le transport dans un
`TraceTransport` qui écrit chaque échange dans `~/CarConnect/logs/` (voir [depannage.md](depannage.md)).

## Transports

Interface `Transport` (`transport/base.py`) : `open()`, `close()`, `write(bytes)`, `read(timeout) -> bytes`.

| Classe | Usage |
|---|---|
| `BleTransport` | Bluetooth Low Energy via `bleak`. **Seul transport utilisé par l'interface** pour un vrai adaptateur. Choisit une caractéristique *notify* (réception) et une *write* (émission) dans le même service, hors services génériques `0x1800`/`0x1801`. Écrit par paquets de 20 octets. |
| `BluetoothTransport` | Bluetooth classique (RFCOMM, profil série), socket Python. Pas branché dans l'interface. |
| `SerialTransport` | Port série réel ou virtuel (`/dev/rfcomm0`, `COMx`) via `pyserial`. Pas branché dans l'interface. |
| `SimulatedTransport` | Faux ELM327 et faux véhicule. |
| `TraceTransport` | Enveloppe un autre transport et journalise les échanges dans un fichier. |

Pour supporter un adaptateur Bluetooth classique, brancher `BluetoothTransport` dans `Backend` et ajouter une
recherche (BlueZ, `bluetoothctl`) : seule la recherche BLE existe aujourd'hui (`transport/ble_scan.py`).

## ELM327 (`elm327/`)

`Elm327.send(cmd)` écrit la commande suivie de `\r`, lit jusqu'au prompt `>` (délai 10 s par défaut), puis nettoie : écho,
lignes vides, `SEARCHING...`, `BUS INIT`. Il lève :

- `NoDataError` pour `NO DATA` (PID non supporté, personne ne répond) ;
- `Elm327Error` pour `?` (commande inconnue), `UNABLE TO CONNECT`, `CAN ERROR`, `BUS ERROR`, `BUFFER FULL`, délai dépassé, etc.

`NoDataError` et `Elm327Timeout` sont deux sous-classes d'`Elm327Error` : la première veut dire que le véhicule n'a pas
répondu (normal), la seconde que c'est l'adaptateur qui se tait (liaison probablement perdue).

`initialize()` envoie `ATZ`, puis `ATE0` (pas d'écho), `ATL0` (pas de saut de ligne), `ATS0` (pas d'espaces),
`ATH0` (pas d'en-têtes) et `ATSP0` (protocole automatique). `restore_obd()` sert après toute requête vers un calculateur
précis, car `ATSH` change l'adresse d'envoi de façon persistante : elle remet d'abord seulement l'adresse (`ATSH7DF`) et
le délai (`ATST32`), pour ne pas relancer la détection du protocole ; si cela échoue, elle fait `ATD` puis la séquence
complète. `protocol()` renvoie le protocole détecté (`ATDPN`).

`isotp.split_messages(lignes)` sépare les lignes de réponse en messages : chaque ligne `62 F1 90 …` est un message à elle
seule (un calculateur peut répondre `7F 22 78`, « réponse en attente », puis la vraie réponse), et une ligne de longueur
sur 3 chiffres (`014`) ouvre un message multi-trame dont les lignes `0: …`, `1: …` sont rassemblées puis tronquées
à la longueur annoncée. Les lignes illisibles sont ignorées.

## OBD-II (`obd/`)

| Fichier | Rôle |
|---|---|
| `client.py` | `ObdClient` : services 01 (temps réel), 02 (données figées), 03 / 07 / 0A (défauts), 04 (effacement), 09 (VIN) |
| `pids.py` | Table `PIDS` : code, clé, nom, unité, formule de décodage (SAE J1979) |
| `dtc.py` | Octets ↔ code (`0x01 0x33` ↔ `P0133`) |
| `dtc_db.py` | Descriptions en français, et déduction depuis la structure du code |
| `readiness.py` | Décodage des moniteurs de préparation (essence ou diesel) |

Hypothèse : véhicule en **CAN** (OBD-II depuis 2008). Pour les défauts, un octet de comptage précède les codes ; les
réponses sans cet octet (anciens protocoles) sont gérées par la parité de la longueur.

`supported_pids()` suit la chaîne des plages (`0100`, `0120`, `0140`…) tant que le dernier bit annonce une plage suivante.

## UDS (`uds/`)

Lecture seule : services `0x3E`, `0x22` et `0x19`. `UdsClient.select(tx)` fait `ATSH`, `request` renvoie la réponse
positive ou lève `UdsNegativeResponse(service, nrc)`. `scan_modules` sonde `0x700`–`0x7E7` (sauf `0x7DF`) avec un délai
de réponse réduit (`ATST20`) et rétablit la configuration OBD-II dans un `finally`. Il refuse de démarrer si le
protocole n'est pas du CAN 11 bits, et s'arrête après trois erreurs de bus consécutives (une absence de réponse
`NO DATA` est normale et ne compte pas). Détails et limites :
[manufacturer-diagnostics.md](manufacturer-diagnostics.md).

## Session et enregistrement

`Session` :

1. ouvre le transport et initialise l'adaptateur (`on_ready`) ;
2. découvre : mesures supportées, VIN, voyant moteur (`on_info`) ;
3. boucle : tâches en attente, puis les mesures rapides (`POLLED_PIDS` : régime, vitesse, température, papillon, charge,
   tension, si supportées) plus **une** mesure lente prise en rotation (`on_sample`).

`Recorder` écrit une ligne CSV par échantillon, avec l'état complet des mesures (les valeurs lentes sont conservées
entre deux rafraîchissements). Les colonnes sont fixées au démarrage de l'enregistrement.

## Interface (`ui/`)

`Backend` expose à QML des propriétés (`values`, `info`, `status`, `connected`, `dtcs`, `readiness`, `freeze`,
`modules`, `moduleReport`, `devices`, `recording`…) et des slots (`connectSimulator`, `autoConnect`, `readDtcs(kind)`,
`readReadiness`, `scanModules`, `startRecording`…). Chaque propriété a un signal de notification ; les mises à jour du
bilan, des données figées et des calculateurs partagent le signal `diagChanged`.

Fichiers QML : `Main.qml` (fenêtre, onglets), `Gauge.qml` (cadran dessiné sur un `Canvas`), `Tile.qml` (tuile). Le style est
`Material` en thème sombre ; il est fixé dans `ui/app.py` avant le chargement du QML.

## Simulateur

`SimulatedTransport` répond comme un ELM327 v1.5 et simule un véhicule dont les valeurs varient avec l'horloge (régime et
vitesse sinusoïdaux). Il accepte une horloge en paramètre pour que les tests soient déterministes.

- OBD-II : mesures (une vingtaine de PIDs), VIN multi-trame, défauts mémorisés et en attente, données figées (seulement s'il
  y a un défaut), moniteurs de préparation, effacement.
- UDS : trois calculateurs fictifs (`0x7E0`, `0x760`, `0x726`) avec identifiants et défauts.
- Fidélité : écho par défaut (désactivé par `ATE0`), `ATD` qui réinitialise, `ATSH` qui change d'adresse, `ATH1`.

Il valide la logique de l'application, **pas** le comportement d'un vrai véhicule ni d'un vrai adaptateur.

## Tests

```fish
poetry run pytest
```

Aucun test ne nécessite de matériel. Ils couvrent : codes défaut (encodage, descriptions), ELM327 et OBD-II contre le
simulateur, moniteurs, enregistrement CSV, UDS, session, détection d'adaptateurs BLE, et un test de bout en bout du
`Backend` Qt avec le simulateur. Le BLE réel, le QML et le rendu ne sont pas testés automatiquement.

## Étendre

| Je veux… | Faire |
|---|---|
| Ajouter une mesure | Une ligne `Pid(...)` dans `obd/pids.py`. Elle apparaît seule dans l'onglet Mesures si le véhicule la supporte. Ajouter sa valeur dans `_pid_values` du simulateur pour la tester |
| Ajouter des descriptions de codes | Entrées dans `obd/dtc_db.py` (`P0xxx` : les numéros de cylindre sont en décimal) |
| Ajouter un transport | Sous-classe de `Transport`, puis l'utiliser dans `Backend._start` |
| Ajouter un identifiant UDS lu | `IDENTIFICATION` dans `uds/client.py` (lecture seule uniquement) |
| Ajouter un onglet | Propriétés et slots dans `Backend`, `TabButton` et page dans `Main.qml` |

## Conventions

- Code et commentaires en français pour ce qui est visible de l'utilisateur ; identifiants en anglais.
- La couche `uds/` ne doit jamais contenir de service d'écriture sans décision explicite et confirmation dans l'interface.
- Les véhicules sont supposés en CAN 11 bits, 500 kbit/s, tant que rien d'autre n'est nécessaire.
