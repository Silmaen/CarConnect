# CarConnect

Application de bureau (Python + PySide6/QML) pour diagnostiquer un véhicule via un adaptateur
OBD-II ELM327 Bluetooth. Véhicules visés : Ford B-MAX, Renault Scénic.

## Démarrage

L'environnement virtuel est géré par [Poetry](https://python-poetry.org/) (rien n'est installé dans le Python système).

```fish
poetry config virtualenvs.in-project true --local   # optionnel : .venv dans le projet (PyCharm le détecte)
poetry install
poetry run carconnect    # lance l'interface (bouton « Simulateur » pour tester sans voiture)
poetry run pytest        # tests
```

## Architecture

| Module | Rôle |
|---|---|
| `transport/` | Canal d'octets : Bluetooth RFCOMM, port série, simulateur ELM327 |
| `elm327/` | Protocole AT : initialisation, envoi, nettoyage des réponses |
| `obd/` | OBD-II générique : PIDs, codes défaut (DTC) |
| `session.py` | Thread de lecture cyclique + file de tâches (lecture/effacement des DTC) |
| `ui/` | Interface Qt/QML (`backend.py` fait le pont, `qml/` les écrans) |

## Feuille de route

1. OBD-II générique (fait : PIDs temps réel, lecture/effacement des DTC).
2. Test sur l'adaptateur réel (Bluetooth classique ou BLE ? à vérifier).
3. Descriptions des codes défaut (base de données).
4. Couche UDS constructeur (`uds/`) avec profils Ford et Renault.
5. Empaquetage en exécutable (PyInstaller, QML inclus).
