import re

_LENGTH_LINE = re.compile(r"^[0-9A-Fa-f]{3}$")


def split_messages(lines: list[str]) -> list[bytes]:
    """Sépare les lignes d'une réponse de l'ELM327 en messages ISO-TP distincts.

    - une ligne d'octets ("62 F1 90 ...") est un message à elle seule : un calculateur peut en envoyer
      plusieurs ("7F 22 78" -- réponse en attente -- puis la vraie réponse), ou plusieurs calculateurs répondre ;
    - une ligne de longueur sur 3 chiffres ("014") ouvre un message multi-trame, dont les lignes
      "0: ...", "1: ..." sont rassemblées puis tronquées à la longueur annoncée (on retire le bourrage).

    Les lignes illisibles sont ignorées.
    """
    messages: list[tuple[int | None, bytearray]] = []
    current: tuple[int | None, bytearray] | None = None
    for line in lines:
        if _LENGTH_LINE.match(line):
            current = (int(line, 16), bytearray())
            messages.append(current)
            continue
        head, colon, payload = line.partition(":")
        try:
            chunk = bytes.fromhex(payload if colon else line)
        except ValueError:
            continue
        if colon:
            if current is None:
                current = (None, bytearray())
                messages.append(current)
            current[1].extend(chunk)
        else:
            current = None
            messages.append((None, bytearray(chunk)))
    return [bytes(data[:size] if size else data) for size, data in messages if data]
