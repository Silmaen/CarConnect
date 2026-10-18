# CarConnect

Application de bureau (Python, PySide6/QML) pour diagnostiquer un véhicule depuis un PC, avec un adaptateur
OBD-II **ELM327 Bluetooth Low Energy**. Véhicules visés : Ford B-MAX et Renault Scénic.

> **Avertissement** : l'application lit les données du véhicule. La seule écriture qu'elle sait faire est l'effacement
> des codes défaut OBD-II (service 04), demandé explicitement et confirmé. Utilise-la à l'arrêt, sans conduire en
> la regardant. Aucune garantie n'est donnée : elle est développée pour un usage personnel.

## Ce qu'elle fait

| Fonction | Détail |
|---|---|
| Connexion | Recherche automatique de l'adaptateur BLE, ou choix dans la liste des appareils vus |
| Mesures temps réel | Régime, vitesse, températures, charge, tension et toutes les mesures OBD-II que le véhicule déclare supporter |
| Identification | VIN, voyant moteur (MIL), nombre de codes défaut |
| Codes défaut | Mémorisés, en attente, permanents, avec description en français ; effacement avec confirmation |
| Bilan | Moniteurs de préparation (prêt pour le contrôle technique) et données figées du premier défaut |
| Enregistrement | Export des mesures en CSV |
| Calculateurs (UDS) | Recherche des calculateurs, identification et défauts constructeur, **en lecture seule** |
| Simulateur | Faux véhicule intégré, pour tester l'application sans voiture |

Ce qu'elle **ne fait pas** : codage, adaptations, réinitialisations constructeur, mise à jour de calculateurs,
données propres à une marque (PIDs constructeur, noms de calculateurs). Voir
[docs/manufacturer-diagnostics.md](docs/manufacturer-diagnostics.md) pour les limites du diagnostic constructeur.

## Prérequis

- Linux avec Bluetooth (BlueZ). Le code est portable, mais seul Linux est testé.
- Python 3.11 à 3.14 et [Poetry](https://python-poetry.org/). Rien n'est installé dans le Python du système.
- Un adaptateur ELM327 **Bluetooth Low Energy**. Un adaptateur Bluetooth classique (SPP) n'est pas pris en charge par
  l'interface (voir [docs/architecture.md](docs/architecture.md#transports)).

## Installation et lancement

```fish
poetry install            # crée .venv dans le projet (poetry.toml) et installe les dépendances
poetry run carconnect     # lance l'application
poetry run pytest         # lance les tests
```

Premier essai sans voiture : cliquer sur **Simulateur** en haut à droite.

## Documentation

| Document | Pour qui | Contenu |
|---|---|---|
| [docs/utilisation.md](docs/utilisation.md) | Utilisateur | Se connecter, lire les onglets, enregistrer, bonnes pratiques |
| [docs/depannage.md](docs/depannage.md) | Utilisateur | Problèmes courants et leurs causes |
| [docs/architecture.md](docs/architecture.md) | Développeur | Couches, threads, protocoles, simulateur, tests, comment étendre |
| [docs/manufacturer-diagnostics.md](docs/manufacturer-diagnostics.md) | Développeur | Recherche et limites du diagnostic constructeur |

## Organisation du dépôt

```
src/carconnect/
  transport/   canal d'octets : BLE, Bluetooth classique, port série, simulateur
  elm327/      dialogue avec l'adaptateur (commandes AT, ISO-TP)
  obd/         OBD-II générique : PIDs, codes défaut, données figées, moniteurs
  uds/         diagnostic constructeur en lecture seule
  session.py   thread de lecture cyclique et file de tâches
  recorder.py  export CSV
  ui/          interface Qt/QML
docs/          documentation
tests/         tests automatiques (sans matériel : ils utilisent le simulateur)
```

## État du projet

| Étape | État |
|---|---|
| OBD-II générique (mesures, VIN, défauts, données figées, moniteurs, CSV) | Fait, testé avec le simulateur |
| Connexion BLE réelle | Validée : le régime moteur est lu |
| Autres fonctions OBD-II sur véhicule réel | À valider (VIN, liste des mesures, bilan, défauts) |
| Diagnostic constructeur (UDS) | Socle écrit, **jamais essayé sur une voiture** |
| Profils par véhicule (noms des calculateurs) | À faire, dépend des résultats du scan |
| Exécutable autonome (PyInstaller) | À faire |

Aucune licence n'est encore choisie : tous droits réservés par défaut.
