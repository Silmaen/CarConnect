"""Diagnostic UDS (ISO 14229) en lecture seule, par-dessus l'ISO-TP géré par l'ELM327.

Seuls des services de lecture sont implémentés : 0x3E (tester present), 0x22 (lecture d'identifiants)
et 0x19 (lecture des défauts). Aucune écriture, aucun effacement, aucun codage.
"""

from dataclasses import dataclass

from carconnect.elm327 import Elm327, Elm327Error, Elm327Timeout, NoDataError
from carconnect.elm327.isotp import split_messages
from carconnect.obd.dtc import decode_dtc
from carconnect.obd.dtc_db import describe

_NRC = {
    0x10: "refus général",
    0x11: "service non supporté",
    0x12: "sous-fonction non supportée",
    0x13: "longueur ou format incorrect",
    0x22: "conditions non remplies",
    0x31: "identifiant inconnu",
    0x33: "accès refusé (sécurité)",
    0x78: "réponse en attente",
}

# Identifiants standard (ISO 14229, plage F1xx)
IDENTIFICATION = {
    0xF190: "VIN",
    0xF187: "Référence pièce",
    0xF18C: "Numéro de série",
    0xF191: "Version matérielle",
    0xF194: "Version logicielle",
}


class UdsNegativeResponse(Elm327Error):
    def __init__(self, service: int, nrc: int) -> None:
        self.service = service
        self.nrc = nrc
        super().__init__(f"refus du service {service:02X} : {_NRC.get(nrc, 'code ' + format(nrc, '02X'))}")


# Bits de l'octet de statut d'un défaut (ISO 14229-1)
STATUS_TEST_FAILED = 0x01
STATUS_PENDING = 0x04
STATUS_CONFIRMED = 0x08
STATUS_WARNING_INDICATOR = 0x80
# Un calculateur stocke aussi des dizaines de codes "supportés mais test pas encore passé" : le masque 0xFF
# les ramène tous (plus de 400 octets sur un Ford, que l'adaptateur ne transmet pas en entier). On ne demande
# donc que les défauts en cours, en attente, confirmés ou qui demandent le voyant.
DEFAULT_STATUS_MASK = STATUS_TEST_FAILED | STATUS_PENDING | STATUS_CONFIRMED | STATUS_WARNING_INDICATOR


@dataclass(frozen=True)
class UdsDtc:
    code: str
    ftb: int  # octet de type de défaut
    status: int

    @property
    def active(self) -> bool:
        return bool(self.status & STATUS_TEST_FAILED)

    @property
    def pending(self) -> bool:
        return bool(self.status & STATUS_PENDING)

    @property
    def confirmed(self) -> bool:
        return bool(self.status & STATUS_CONFIRMED)

    @property
    def warning(self) -> bool:
        return bool(self.status & STATUS_WARNING_INDICATOR)

    def state(self) -> str:
        labels = (("actif", self.active), ("en attente", self.pending), ("confirmé", self.confirmed), ("voyant", self.warning))
        return ", ".join(label for label, on in labels if on) or "historique"


def announced_length(frames: list[str]) -> int | None:
    """Longueur annoncée par une première trame ISO-TP, dans une réponse à en-têtes ("7E8 11 9F 59 …")."""
    for frame in frames:
        try:
            data = bytes.fromhex(frame[3:])  # après l'identifiant CAN sur 3 chiffres
        except ValueError:
            continue
        if len(data) >= 2 and data[0] >> 4 == 1:
            return ((data[0] & 0x0F) << 8) | data[1]
    return None


class UdsClient:
    def __init__(self, elm: Elm327) -> None:
        self._elm = elm

    def select(self, tx_id: int) -> None:
        """Adresse les requêtes à un calculateur (identifiant CAN 11 bits ; la réponse est attendue à tx+8)."""
        self._elm.send(f"ATSH{tx_id:03X}")

    def request(self, service: int, data: bytes = b"") -> bytes:
        """Envoie une requête et renvoie la réponse positive sans son octet de service.

        Un calculateur peut répondre "7F service 78" (réponse en attente) avant la vraie réponse : cette
        ligne est ignorée si une réponse définitive la suit.
        """
        messages = split_messages(self._elm.send((bytes([service]) + data).hex().upper()))
        refusal = None
        for message in messages:
            if message[0] == 0x7F and len(message) >= 3 and message[1] == service:
                pending = message[2] == 0x78
                if refusal is None or not pending:
                    refusal = UdsNegativeResponse(service, message[2])
            elif message[0] == service + 0x40:
                return message[1:]
        if refusal:
            raise refusal
        if not messages:
            raise NoDataError(f"{service:02X}")
        raise Elm327Error(f"réponse inattendue : {' | '.join(m.hex(' ').upper() for m in messages)}")

    def raw_frames(self, service: int, data: bytes = b"") -> list[str]:
        """Réponse brute avec les en-têtes CAN (identifiant et octet PCI), pour comprendre une réponse illisible."""
        self._elm.send("ATH1")
        try:
            return self._elm.send((bytes([service]) + data).hex().upper())
        finally:
            self._elm.send("ATH0")

    def tester_present(self) -> None:
        self.request(0x3E, b"\x00")

    def read_did(self, did: int) -> bytes:
        payload = self.request(0x22, did.to_bytes(2, "big"))
        if payload[:2] != did.to_bytes(2, "big"):
            raise Elm327Error(f"identifiant inattendu : {payload[:2].hex()}")
        return payload[2:]

    def identification(self) -> dict[str, str]:
        """Identifiants standard que le calculateur accepte de donner."""
        found = {}
        for did, label in IDENTIFICATION.items():
            try:
                found[label] = self.read_did(did).decode("ascii", "replace").strip("\x00 ")
            except Elm327Timeout:
                raise
            except Elm327Error:  # refus, absence de réponse ou réponse illisible : on passe au suivant
                pass
        return found

    def read_dtcs(self, mask: int = DEFAULT_STATUS_MASK) -> list[UdsDtc]:
        """Codes défaut (service 19, sous-fonction 02) dont l'octet de statut a un bit commun avec `mask`."""
        payload = self.request(0x19, bytes([0x02, mask]))
        records = payload[2:]  # sous-fonction et masque de disponibilité en tête
        dtcs = []
        for i in range(0, len(records) - 3, 4):
            b0, b1, ftb, status = records[i : i + 4]
            if (b0, b1, ftb) != (0, 0, 0):
                dtcs.append(UdsDtc(decode_dtc(b0, b1), ftb, status))
        return dtcs


def module_report(uds: UdsClient, tx_id: int) -> str:
    """Rapport texte d'un calculateur : identification et défauts (lecture seule).

    Un calculateur qui refuse ou répond de travers est décrit dans le rapport au lieu de faire échouer la lecture.
    """
    lines = [f"Calculateur {tx_id:#05x} → {tx_id + 8:#05x}"]
    identification = uds.identification()
    lines += [f"{label} : {value}" for label, value in identification.items()]
    if not identification:
        lines.append("Identification : non disponible")
    try:
        dtcs = uds.read_dtcs()
    except Elm327Timeout:
        raise
    except (UdsNegativeResponse, NoDataError) as exc:
        lines.append(f"Défauts : lecture impossible ({exc})")
    except Elm327Error as exc:  # réponse illisible : on joint les trames brutes pour pouvoir l'analyser
        lines.append(f"Défauts : lecture impossible ({exc})")
        try:
            raw = uds.raw_frames(0x19, bytes([0x02, DEFAULT_STATUS_MASK]))
            lines.append("  Trames brutes : " + (" | ".join(raw) or "aucune"))
            length = announced_length(raw)
            if length and length > 7:
                lines.append(
                    f"  Le calculateur annonce {length} octets en plusieurs trames, "
                    "mais l'adaptateur n'en transmet que la première."
                )
        except Elm327Timeout:
            raise
        except Elm327Error as raw_exc:
            lines.append(f"  Trames brutes indisponibles ({raw_exc})")
    else:
        lines.append(f"Défauts : {len(dtcs)}" if dtcs else "Défauts : aucun")
        for dtc in dtcs:
            lines.append(f"  {dtc.code}  {describe(dtc.code)}  [{dtc.state()}]")
    return "\n".join(lines)
