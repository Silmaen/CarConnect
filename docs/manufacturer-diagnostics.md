# Diagnostic constructeur (Ford B-MAX, Renault Scénic)

Notes de recherche et décisions de conception. À mettre à jour après les premiers essais sur les voitures.

## Ce que dit l'état de l'art

| Outil | Cible | Ouvert ? | Remarques |
|---|---|---|---|
| [DDT4all](https://github.com/cedricp/ddt4all) | Renault / Dacia | Code oui, **données non** | ISO-TP, KWP2000 et UDS via ELM327. Exige la base DDT2000, propriété de Renault, non fournie pour des raisons juridiques. Prévu pour un ELM327 d'origine (PIC18F25K80) : beaucoup de clones ne fonctionnent pas. |
| FORScan | Ford / Mazda | Non | Windows. La plupart des modules Ford passent par le **MS-CAN** (broches OBD 3 et 11), absent d'un ELM327 standard ; il faut un adaptateur modifié avec commutateur HS/MS-CAN (broches 6 et 14 pour le HS-CAN). |

Sources : [DDT4all](https://github.com/Furtif/ddt4all), [FORScan : accès au MS-CAN](https://forum.forscan.org/viewtopic.php?p=4), [commandes AT de l'ELM327](https://cdn.sparkfun.com/assets/4/e/5/0/2/ELM327_AT_Commands.pdf).

## Ce que le dépôt fait aujourd'hui (`uds/`)

Diagnostic **UDS en lecture seule**, sans base de données constructeur :

- recherche des calculateurs : un « tester present » (service `0x3E`) à chaque identifiant CAN 11 bits de `0x700` à `0x7E7` ;
- identification par les identifiants standard `F190` (VIN), `F187`, `F18C`, `F191`, `F194` (service `0x22`) ;
- lecture des codes défaut (service `0x19`, sous-fonction `0x02`), filtrés sur les statuts actif, en attente, confirmé ou
  voyant demandé, avec description générique.

L'ISO-TP (multi-trames, contrôle de flux) est géré par l'ELM327 ; le code ne fait que `ATSH` pour choisir le calculateur, puis rassemble les lignes de réponse.

**Garde-fous** : aucun service d'écriture, d'effacement, de codage, de routine ou d'accès sécurité n'est implémenté. L'effacement de codes n'existe que pour l'OBD-II générique (service 04), derrière une confirmation.

## Limites connues

- **Convention de réponse `tx + 8`** : c'est celle de l'ELM327 par défaut (`ATAR`). Les calculateurs qui répondent ailleurs ne sont pas vus. C'est probablement le cas de certains calculateurs Renault.
- **CAN 11 bits seulement** ; pas de CAN 29 bits, de KWP2000 sur K-line ni de DoIP.
- **Seul le HS-CAN est atteint** (broches 6/14). Sur le Ford, les modules du MS-CAN (carrosserie, combiné, clim, etc., à vérifier sur le B-MAX) demandent un adaptateur compatible.
- **Pas de noms de calculateurs ni de PIDs constructeur** : ils viennent des bases propriétaires. Le logiciel affiche des adresses, pas « ABS » ou « BCM ».
- **Codes `B`, `C`, `U` et `P1xxx`** : seule une description structurelle est donnée (système, générique ou constructeur).
- La réponse négative `0x78` (réponse en attente) n'est pas gérée : l'ELM327 attend normalement la réponse finale.

## Premier essai réel (Ford, calculateur moteur `0x7E0`)

Résultats d'un essai avec un ELM327 BLE bon marché, sur une voiture à boîte manuelle :

- Seul le calculateur moteur répond au scan (`0x7E0`). La boîte (`0x7E1`) ne répond pas, ce qui est normal sans boîte
  automatique. Le reste du véhicule n'est pas sur le bus accessible.
- Identification : VIN (`F190`) et numéro de série (`F18C`) sont lus ; référence pièce, versions matérielle et logicielle
  sont refusées (`7F 22 31`, identifiant inconnu).
- **Lecture des défauts avec le masque de statut `0xFF`** : le calculateur répond par un message de 415 octets (environ
  100 enregistrements). Ce sont presque tous des codes « supportés mais test pas encore passé », pas des défauts. Le
  clone n'en transmet que la première trame (`7E8 11 9F 59 02 FF 03 28 12`), d'où une réponse illisible.
- **Correction** : on demande seulement les défauts en cours, en attente, confirmés ou demandant le voyant (masque
  `0x8D`, `DEFAULT_STATUS_MASK`). C'est aussi ce que fait l'autre programme testé, qui annonce « aucun défaut ».

Leçon : un clone ELM327 ne transmet pas fiablement les longs messages multi-trames. Les réponses courtes et moyennes
(27 octets pour le VIN) passent. Le rapport d'un calculateur joint les trames brutes quand une réponse est illisible.

## Droit et données

La base DDT2000 est la propriété de Renault : le dépôt ne la contient pas et ne doit pas la redistribuer. Si un import est un jour ajouté, il lira un fichier fourni par l'utilisateur, en local.

## Suite proposée

1. **Essayer le scan sur chaque voiture** (contact mis) et noter les identifiants qui répondent. Sans ces résultats, impossible de savoir ce qui est joignable.
2. **Profils par véhicule** (`profiles/*.json`) : l'utilisateur associe un nom à chaque identifiant trouvé ; l'appli les affiche ensuite.
3. **Journal brut des échanges** (option) pour comprendre ce que les calculateurs acceptent.
4. Si le Ford refuse de répondre sur le MS-CAN : vérifier la compatibilité d'un adaptateur plus capable (puce STN, p. ex. gamme OBDLink) **avant tout achat**.
5. Éventuellement, un import local de la base DDT4all fournie par l'utilisateur, pour les PIDs et les noms de calculateurs Renault.
