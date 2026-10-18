"""Descriptions des codes défaut : table des codes génériques courants, sinon déduction depuis la structure du code."""

_SYSTEMS = {
    "P": "Groupe motopropulseur",
    "C": "Châssis",
    "B": "Carrosserie",
    "U": "Réseau de communication",
}
_P_AREAS = {
    "0": "mesure d'air et de carburant",
    "1": "mesure d'air et de carburant",
    "2": "injecteurs, turbo et circuits de carburant",
    "3": "allumage et ratés d'allumage",
    "4": "contrôle auxiliaire des émissions",
    "5": "vitesse, ralenti et entrées auxiliaires",
    "6": "calculateur et circuits de sortie",
    "7": "transmission",
    "8": "transmission",
    "9": "transmission",
    "A": "propulsion hybride",
    "B": "propulsion hybride",
    "C": "propulsion hybride",
}

_SENSOR_FAULTS = ("circuit", "signal bas", "signal haut", "réponse lente", "aucune activité détectée", "circuit du chauffage")


def _build() -> dict[str, str]:
    d: dict[str, str] = {}

    # Sondes O2 : 6 codes par capteur
    for base, label in (
        (0x0130, "banc 1 capteur 1"),
        (0x0136, "banc 1 capteur 2"),
        (0x0142, "banc 1 capteur 3"),
        (0x0150, "banc 2 capteur 1"),
        (0x0156, "banc 2 capteur 2"),
        (0x0162, "banc 2 capteur 3"),
    ):
        for i, fault in enumerate(_SENSOR_FAULTS):
            d[f"P{base + i:04X}"] = f"Sonde O2 ({label}) : {fault}"
    # Les numéros de cylindre et de bobine s'écrivent en décimal dans le code : cylindre 10 -> P0310, pas P030A
    for n in range(1, 13):
        d[f"P02{n:02d}"] = f"Circuit de l'injecteur du cylindre {n}"
        d[f"P03{n:02d}"] = f"Raté d'allumage détecté sur le cylindre {n}"
    for n, letter in enumerate("ABCDEFGHIJKL", start=51):
        d[f"P03{n:02d}"] = f"Bobine d'allumage {letter} : circuit primaire/secondaire"

    d.update(
        {
            "P0016": "Corrélation vilebrequin / arbre à cames (banc 1 capteur A)",
            "P0100": "Circuit du débitmètre d'air (MAF)",
            "P0101": "Débitmètre d'air : plage / performance",
            "P0102": "Débitmètre d'air : signal bas",
            "P0103": "Débitmètre d'air : signal haut",
            "P0105": "Circuit du capteur de pression d'admission (MAP)",
            "P0106": "Capteur MAP : plage / performance",
            "P0107": "Capteur MAP : signal bas",
            "P0108": "Capteur MAP : signal haut",
            "P0110": "Circuit du capteur de température d'air d'admission",
            "P0111": "Température d'air d'admission : plage / performance",
            "P0112": "Température d'air d'admission : signal bas",
            "P0113": "Température d'air d'admission : signal haut",
            "P0115": "Circuit du capteur de température du liquide de refroidissement",
            "P0116": "Température du liquide : plage / performance",
            "P0117": "Température du liquide : signal bas",
            "P0118": "Température du liquide : signal haut",
            "P0120": "Circuit du capteur de position papillon / pédale A",
            "P0121": "Capteur papillon / pédale A : plage / performance",
            "P0122": "Capteur papillon / pédale A : signal bas",
            "P0123": "Capteur papillon / pédale A : signal haut",
            "P0125": "Température du liquide insuffisante pour la boucle fermée",
            "P0128": "Thermostat : température du liquide inférieure à la normale",
            "P0171": "Mélange trop pauvre (banc 1)",
            "P0172": "Mélange trop riche (banc 1)",
            "P0174": "Mélange trop pauvre (banc 2)",
            "P0175": "Mélange trop riche (banc 2)",
            "P0200": "Circuit des injecteurs",
            "P0217": "Surchauffe du moteur",
            "P0219": "Survitesse du moteur",
            "P0220": "Circuit du capteur de position papillon / pédale B",
            "P0234": "Suralimentation excessive (turbo)",
            "P0235": "Circuit du capteur de pression de suralimentation A",
            "P0299": "Suralimentation insuffisante (turbo)",
            "P0300": "Ratés d'allumage multiples ou aléatoires",
            "P0325": "Circuit du capteur de cliquetis 1",
            "P0327": "Capteur de cliquetis 1 : signal bas",
            "P0328": "Capteur de cliquetis 1 : signal haut",
            "P0335": "Circuit du capteur de position vilebrequin A",
            "P0336": "Capteur vilebrequin A : plage / performance",
            "P0337": "Capteur vilebrequin A : signal bas",
            "P0338": "Capteur vilebrequin A : signal haut",
            "P0340": "Circuit du capteur d'arbre à cames A (banc 1)",
            "P0341": "Capteur d'arbre à cames A : plage / performance",
            "P0342": "Capteur d'arbre à cames A : signal bas",
            "P0343": "Capteur d'arbre à cames A : signal haut",
            "P0380": "Circuit de commande des bougies de préchauffage A",
            "P0381": "Circuit du témoin de préchauffage",
            "P0400": "Recirculation des gaz d'échappement (EGR) : débit",
            "P0401": "EGR : débit insuffisant",
            "P0402": "EGR : débit excessif",
            "P0403": "Circuit de commande de l'EGR",
            "P0404": "EGR : plage / performance",
            "P0405": "Capteur EGR A : signal bas",
            "P0406": "Capteur EGR A : signal haut",
            "P0410": "Système d'air secondaire",
            "P0420": "Efficacité du catalyseur inférieure au seuil (banc 1)",
            "P0430": "Efficacité du catalyseur inférieure au seuil (banc 2)",
            "P0440": "Système de contrôle des vapeurs de carburant (EVAP)",
            "P0441": "EVAP : débit de purge incorrect",
            "P0442": "EVAP : petite fuite détectée",
            "P0443": "Circuit de la vanne de purge EVAP",
            "P0446": "Circuit de commande de ventilation EVAP",
            "P0455": "EVAP : grosse fuite détectée",
            "P0456": "EVAP : très petite fuite détectée",
            "P0460": "Circuit du capteur de niveau de carburant",
            "P0461": "Capteur de niveau de carburant : plage / performance",
            "P0480": "Circuit de commande du ventilateur de refroidissement 1",
            "P0481": "Circuit de commande du ventilateur de refroidissement 2",
            "P0500": "Capteur de vitesse du véhicule",
            "P0501": "Capteur de vitesse du véhicule : plage / performance",
            "P0505": "Système de régulation du ralenti",
            "P0506": "Ralenti plus bas que prévu",
            "P0507": "Ralenti plus haut que prévu",
            "P0510": "Contacteur de papillon fermé",
            "P0560": "Tension du système",
            "P0562": "Tension du système basse",
            "P0563": "Tension du système haute",
            "P0571": "Circuit du contacteur de frein A (régulateur de vitesse)",
            "P0600": "Liaison de communication série",
            "P0601": "Calculateur : erreur de somme de contrôle mémoire",
            "P0602": "Calculateur : erreur de programmation",
            "P0603": "Calculateur : erreur mémoire KAM",
            "P0604": "Calculateur : erreur de RAM",
            "P0605": "Calculateur : erreur de ROM",
            "P0606": "Calculateur : défaut du processeur",
            "P0607": "Calculateur : performance",
            "P0627": "Circuit de commande de la pompe à carburant A",
            "P0641": "Alimentation de référence des capteurs A : circuit",
            "P0685": "Circuit de commande du relais principal du calculateur",
            "P0700": "Système de commande de la transmission",
            "P0701": "Commande de transmission : plage / performance",
            "P0705": "Circuit du contacteur de plage de transmission (PRNDL)",
            "P0715": "Circuit du capteur de vitesse d'entrée de transmission",
            "P0720": "Circuit du capteur de vitesse de sortie de transmission",
            "P0730": "Rapport de transmission incorrect",
            "P0740": "Circuit de l'embrayage du convertisseur de couple",
            "P0741": "Embrayage du convertisseur : performance / bloqué ouvert",
            "P0750": "Circuit du solénoïde de changement de rapport A",
            "P0755": "Circuit du solénoïde de changement de rapport B",
            "P2002": "Efficacité du filtre à particules inférieure au seuil (banc 1)",
            "P2096": "Correction de carburant après catalyseur : trop pauvre (banc 1)",
            "P2097": "Correction de carburant après catalyseur : trop riche (banc 1)",
            "P2101": "Circuit du moteur de papillon motorisé A",
            "P2106": "Papillon motorisé : puissance limitée",
            "P2119": "Papillon motorisé : plage / performance",
            "P2135": "Corrélation des capteurs de papillon A / B",
            "P2138": "Corrélation des capteurs de pédale D / E",
            "P2452": "Circuit du capteur de pression différentielle du filtre à particules",
            "P2463": "Filtre à particules : accumulation de suie excessive",
            "U0001": "Bus CAN haute vitesse : communication",
            "U0073": "Bus de communication du calculateur A hors service",
            "U0100": "Communication perdue avec le calculateur moteur (ECM/PCM)",
            "U0101": "Communication perdue avec le calculateur de transmission (TCM)",
            "U0121": "Communication perdue avec le calculateur ABS",
            "U0140": "Communication perdue avec le calculateur de carrosserie (BCM)",
            "U0155": "Communication perdue avec le combiné d'instruments",
        }
    )
    return d


DESCRIPTIONS = _build()


def describe(code: str) -> str:
    """Description française d'un code, ou à défaut ce qu'on peut déduire de sa structure."""
    code = code.upper()
    if code in DESCRIPTIONS:
        return DESCRIPTIONS[code]
    parts = [_SYSTEMS.get(code[:1], "Système inconnu")]
    if code[:2] == "P0" and code[2:3] in _P_AREAS:  # le domaine n'a de sens que pour les codes SAE P0xxx
        parts.append(_P_AREAS[code[2]])
    kind = {"0": "générique (SAE)", "2": "générique (SAE)", "3": "générique ou constructeur"}
    parts.append("code " + kind.get(code[1:2], "propre au constructeur"))
    return " — ".join(parts)
