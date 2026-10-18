# Guide d'utilisation

## Avant de commencer

1. **Brancher l'adaptateur** sur la prise OBD du véhicule. Il est alimenté par la prise : il ne s'allume qu'une fois branché.
2. **Mettre le contact** (ou l'accessoire). Sans contact, l'adaptateur peut répondre alors que le calculateur moteur
   reste muet.
3. **Fermer l'application du téléphone** qui utilise l'adaptateur. Un adaptateur BLE n'accepte en général qu'*une seule*
   connexion à la fois.
4. Pour les essais, éviter de conduire en même temps : l'application demande de l'attention.

## Se connecter

La barre du haut affiche l'état de la connexion (en vert une fois connecté) et trois boutons :

| Bouton | Effet |
|---|---|
| **Rechercher** | Scanne le Bluetooth pendant 5 secondes. Si **un seul** appareil ressemble à un adaptateur OBD, l'application s'y connecte directement. Sinon, elle affiche la liste. |
| **Simulateur** | Se connecte à un faux véhicule intégré, sans matériel. |
| **Déconnecter** | Coupe la connexion (visible une fois connecté). |

### La liste des appareils

Elle montre le nom, l'adresse et la force du signal (en dBm : plus c'est proche de 0, plus le signal est fort). Les
appareils qui ressemblent à un adaptateur OBD sont marqués ★ : nom contenant `OBD`, `ELM327`, `Vgate`, `V-LINK`,
`iCar`, `Viecar`, `Konnwei` ou `OB2`, ou service Bluetooth habituel des ELM327 BLE (`FFF0`, `FFE0`, `18F0`).

Cliquer sur un appareil pour s'y connecter. En bas, on peut aussi saisir une **adresse à la main**
(`AA:BB:CC:DD:EE:FF`) et relancer la recherche.

### Ce qui se passe à la connexion

L'application réinitialise l'adaptateur, détecte le protocole du véhicule (cela peut prendre quelques secondes), puis lit :
la liste des mesures supportées, le VIN, et l'état du voyant moteur. Le statut passe à « Connecté — ELM327 v… ». Les
mesures principales se mettent ensuite à jour en continu.

## Les onglets

### Tableau de bord

- Deux cadrans : **régime** (0 à 7000 tr/min) et **vitesse** (0 à 220 km/h).
- Quatre tuiles : température du liquide de refroidissement, position du papillon, charge moteur, tension.
- Une ligne **VIN · voyant moteur** : « allumé » si le calculateur demande l'allumage du voyant, avec le nombre de codes.

Une valeur absente (mesure non supportée) reste à 0.

### Mesures

Toutes les mesures OBD-II que le véhicule déclare supporter *et* que l'application sait décoder (une trentaine de PIDs
standard : corrections de carburant, pression d'admission, débit d'air, avance, températures, pédale, débit de
carburant…).

- Les six mesures du tableau de bord sont relues à chaque cycle.
- Les autres sont relues **une par cycle, en rotation** : plus il y en a, plus chacune se rafraîchit lentement.

**Enregistrer en CSV** : le bouton démarre l'enregistrement, le chemin du fichier s'affiche à côté. Le fichier est
créé dans `~/CarConnect/` sous le nom `mesures_AAAAMMJJ_HHMMSS.csv` :

- une colonne `time` (secondes depuis le début de l'enregistrement), puis une colonne par mesure ;
- une ligne par lecture. Les mesures lues en rotation gardent leur dernière valeur entre deux rafraîchissements ;
- séparateur virgule, point décimal, encodage UTF-8.

L'enregistrement s'arrête avec le bouton ou à la déconnexion.

### Bilan

- **Moniteurs de préparation** : chaque test d'émissions interne (catalyseur, sondes O2, EVAP, EGR, filtre à particules…)
  est « prêt » ou « non prêt ». Un moniteur « non prêt » signifie que le test n'a pas encore tourné, souvent après
  un effacement de codes ou une coupure de batterie. Le contrôle technique en tient compte.
- **Données figées** : photographie des mesures (régime, température, charge…) prise quand le premier défaut est apparu,
  avec le code qui l'a déclenchée. Absente s'il n'y a aucun défaut mémorisé.

Cliquer sur **Lire** dans chaque cadre pour interroger le véhicule.

### Défauts

| Bouton | Contenu |
|---|---|
| **Mémorisés** | Défauts confirmés (service 03). Ce sont eux qui allument le voyant. |
| **En attente** | Défauts vus une fois, pas encore confirmés (service 07). |
| **Permanents** | Défauts que le calculateur conserve même après effacement, jusqu'à ce que le test soit passé (service 0A). |
| **Effacer** | Efface les codes mémorisés après confirmation. |

Chaque code est affiché avec sa description. Pour les codes absents de la table, l'application déduit au moins le
système (moteur, châssis, carrosserie, réseau) et dit si le code est générique ou propre au constructeur.

**Avant d'effacer** : relever les codes et les données figées, car l'effacement les supprime. Il remet aussi les moniteurs
de préparation à « non prêt ». Si le défaut persiste, le code et le voyant reviennent. Effacer ne répare rien.

### Calculateurs

Diagnostic constructeur en **lecture seule**.

1. **Rechercher les calculateurs** envoie une requête inoffensive (« tester present ») à chaque adresse possible de
   `0x700` à `0x7E7`. C'est long (plusieurs dizaines de secondes, estimation non mesurée) : la lecture des mesures est
   suspendue pendant ce temps. La progression s'affiche.
2. Cliquer sur un calculateur trouvé affiche son **rapport** : identification (VIN, référence pièce, version logicielle —
   selon ce que le calculateur accepte de donner) et codes défaut, avec leur statut (actif, confirmé, historique).

L'application affiche des **adresses**, pas des noms (« ABS », « BCM »…) : ces noms viennent de bases de données
constructeur qu'elle n'a pas. Voir [manufacturer-diagnostics.md](manufacturer-diagnostics.md) pour ce qui est atteignable
ou non avec un ELM327.

## Bonnes pratiques

- Faire les lectures **à l'arrêt**, contact mis ; moteur tournant si l'on veut des mesures en direct.
- Ne pas débrancher l'adaptateur pendant un enregistrement ou un scan.
- Ne pas laisser l'adaptateur branché à demeure : certains consomment assez pour décharger la batterie en quelques jours.
- Ne rien « tester » au hasard : un code effacé à la légère est une information perdue.
