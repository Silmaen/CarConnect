from collections.abc import Callable, Iterable
from dataclasses import dataclass

from carconnect.elm327 import Elm327, Elm327Error, NoDataError

# 0x7E0-0x7E7 : calculateurs OBD-II standard ; 0x7DF est l'adresse fonctionnelle (diffusion), pas un calculateur
DEFAULT_CANDIDATES = range(0x700, 0x7E8)
MAX_CONSECUTIVE_ERRORS = 3


@dataclass(frozen=True)
class Module:
    tx: int  # identifiant de requête
    rx: int  # identifiant de réponse (convention tx + 8)


def scan_modules(
    elm: Elm327,
    candidates: Iterable[int] = DEFAULT_CANDIDATES,
    progress: Callable[[int], None] | None = None,
) -> list[Module]:
    """Cherche les calculateurs qui répondent à un "tester present" (0x3E), un par identifiant.

    Une réponse négative compte aussi : elle prouve que le calculateur est là. Ne repère que les
    calculateurs en CAN 11 bits qui répondent à tx + 8. La configuration OBD-II est rétablie à la fin.

    "Personne à cette adresse" (NO DATA) est normal. Toute autre erreur est comptabilisée : au bout de
    `MAX_CONSECUTIVE_ERRORS` d'affilée, le scan s'arrête au lieu de les prendre pour des absences.
    """
    protocol = elm.protocol()
    if protocol.lstrip("A") not in ("6", "8"):  # ISO 15765-4, CAN 11 bits (500 ou 250 kbit/s)
        raise Elm327Error(f"recherche impossible : CAN 11 bits requis, protocole détecté : {protocol}")
    found = []
    errors = 0
    try:
        elm.send("ATST20")  # délai de réponse court : 32 * 4 ms
        for tx in candidates:
            if tx == 0x7DF:
                continue
            if progress:
                progress(tx)
            try:
                elm.send(f"ATSH{tx:03X}")
                elm.send("3E00")
            except NoDataError:
                errors = 0
                continue
            except Elm327Error as exc:
                errors += 1
                if errors >= MAX_CONSECUTIVE_ERRORS:
                    raise Elm327Error(f"recherche interrompue à {tx:#05x} : {exc}") from exc
                continue
            errors = 0
            found.append(Module(tx, tx + 8))
    finally:
        elm.restore_obd()
    return found
