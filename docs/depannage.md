# Dépannage

Le message d'erreur s'affiche dans la barre du haut (« Erreur : … »). La connexion est alors fermée.

## Connexion

| Symptôme | Cause probable | Que faire |
|---|---|---|
| La recherche ne trouve rien | Adaptateur non alimenté, Bluetooth du PC coupé | Vérifier que l'adaptateur est branché (voyant allumé) ; `bluetoothctl show` doit indiquer `Powered: yes` |
| « Recherche impossible : … » | BlueZ arrêté ou Bluetooth bloqué | `systemctl status bluetooth` ; `rfkill list` |
| L'adaptateur est listé mais la connexion échoue ou expire | Adaptateur déjà connecté (téléphone) | Fermer l'application du téléphone, voire couper son Bluetooth |
| « aucune paire notify/write trouvée ; caractéristiques : … » | Disposition BLE inhabituelle | Noter la liste affichée et l'adapter dans `transport/ble.py` (`_pick`) |
| L'adaptateur est vu mais pas marqué ★ | Nom ou service non reconnu | Le choisir dans la liste, ou saisir son adresse |
| La recherche automatique propose la liste alors qu'il n'y a qu'un adaptateur | Plusieurs appareils ressemblent à un OBD | Choisir le bon dans la liste |

Le bouton **Rechercher** n'est visible que déconnecté. Un adaptateur Bluetooth *classique* (appairage dans les paramètres
système, profil série) n'apparaît pas dans cette recherche : voir [architecture.md](architecture.md#transports).

## Après la connexion

| Message ou symptôme | Cause probable | Que faire |
|---|---|---|
| « Erreur : UNABLE TO CONNECT » | L'adaptateur ne parle pas au calculateur : contact coupé, prise mal enfoncée | Mettre le contact, vérifier la prise, se reconnecter |
| « Erreur : délai dépassé (pas de réponse de l'adaptateur) » | Liaison coupée ou adaptateur bloqué | Se rapprocher, débrancher puis rebrancher l'adaptateur |
| « Erreur : commande inconnue … » | Adaptateur incomplet (clone ELM327 v1.5 mal imité) | Voir ci-dessous |
| « Erreur : CAN ERROR », « BUS ERROR »… | Problème sur le bus | Se reconnecter, contact mis, moteur éteint |
| Connecté mais toutes les valeurs à 0 | Moteur arrêté (le régime vaut 0) ou mesures non supportées | Normal à l'arrêt ; voir l'onglet Mesures pour ce qui est supporté |
| L'onglet Mesures est vide | La liste des mesures supportées n'a pas pu être lue | Se reconnecter ; si ça persiste, essayer contact mis moteur tournant |
| « Aucune donnée figée » | Aucun défaut mémorisé | Normal |
| Les mesures se rafraîchissent lentement | Beaucoup de mesures supportées, lues en rotation | Normal : les six principales restent rapides |
| « Erreur : recherche impossible : CAN 11 bits requis … » | Le véhicule n'est pas en CAN 11 bits (le protocole détecté est affiché sur le tableau de bord) | Le scan UDS ne s'applique pas à ce véhicule |
| « Erreur : recherche interrompue à 0x… » | Trois erreurs de bus d'affilée pendant le scan | Relancer ; noter l'adresse et utiliser le journal des échanges |
| La connexion se ferme pendant ou juste après la recherche de calculateurs | Adaptateur qui supporte mal la rafale de requêtes, ou erreur de bus | Lancer avec le journal des échanges (ci-dessus) et regarder les dernières lignes avant la fermeture |
| Un scan de calculateurs ne trouve rien | Calculateurs sur un autre bus, ou adresses de réponse inhabituelles | Voir [manufacturer-diagnostics.md](manufacturer-diagnostics.md#limites-connues) |

Si une lecture ponctuelle (défauts, bilan, calculateur) échoue, l'erreur s'affiche mais la **connexion reste ouverte**.

## Journal des échanges

Pour comprendre un problème de connexion ou de réponse, lancer l'application avec la variable `CARCONNECT_TRACE` :

```fish
env CARCONNECT_TRACE=1 poetry run carconnect
```

Chaque connexion écrit alors `~/CarConnect/logs/trace_AAAAMMJJ_HHMMSS.log` (chemin rappelé dans la barre d'état). Pour écrire
le journal à un endroit précis, donner le chemin à la place de `1` (il est écrasé à chaque connexion) :

```fish
env CARCONNECT_TRACE=.claudetools/trace.log poetry run carconnect
```

Exemple de contenu :

```
    0.412 >> b'ATZ\r'            # envoyé à l'adaptateur
    1.020 << b'\r\rELM327 v1.5\r\r>'   # reçu
   12.300 !! écriture impossible : …   # erreur de liaison
   12.310 !! session interrompue : …  # erreur qui a fermé la connexion
```

Le temps est en secondes depuis l'ouverture. Le journal contient les identifiants et le VIN lus : le relire avant de le
partager. Les erreurs de l'application elles-mêmes (avec leur trace Python) s'affichent dans le terminal de lancement.

## Adaptateurs et clones

Les ELM327 bon marché annoncent souvent « v2.1 » alors qu'il s'agit d'une puce v1.5 copiée. Conséquences possibles :
commandes AT manquantes, réponses lentes, PIDs ignorés, perte de connexion. Ce n'est pas un défaut de l'application. Un
adaptateur d'une marque connue (puce STN, p. ex. OBDLink) est plus fiable, mais **vérifier sa compatibilité avant achat**.

## Installation et démarrage

| Problème | Piste |
|---|---|
| `poetry install` refuse PySide6 (« Python version … ») | La plage de Python du projet est `>=3.11,<3.15`. Si PySide6 n'a pas encore de version pour ton Python, installer un Python 3.12 ou 3.13 et lancer `poetry env use 3.13` |
| `poetry run pytest` : commande introuvable | Les dépendances de développement ne sont pas installées : `poetry install` |
| L'application ne s'ouvre pas sur un serveur sans écran | Lancer avec `QT_QPA_PLATFORM=offscreen` (aucune fenêtre ne s'affiche) |
| Messages QML dans le terminal | Les noter : ils indiquent le fichier et la ligne concernés dans `ui/qml/` |

## Fichiers créés par l'application

Seuls les enregistrements CSV, dans `~/CarConnect/`. Aucun réglage ni journal n'est écrit ailleurs.
