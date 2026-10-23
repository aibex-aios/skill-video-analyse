"""Hilfsskript des Skills video-analyse (skill-video-analyse 0.1.0).

Aufruf: python3 video_analyse.py <befehl> <argumente>

Befehle:
  lookup <projekt> <url>             vorhandene Video-Notiz zu dieser Video-ID suchen
  pick <info.json>                   Untertitel aus der Ausgabe von yt-dlp -J waehlen
  reserve <projekt> <titel>          Nummer NN ueber @Video/NN.lock reservieren
  transcript <json3> <url> <ziel>    Video-Notiz aus JSON3-Untertiteln schreiben
  release <projekt> <NN>             @Video/NN.lock loeschen

Ausgaben auf stdout sind eine Zeile mit Feldern, getrennt durch Tabulator; Meldungen
gehen auf stderr. Exit 0 erfolgreich, 1 Fehler, 2 keine freie Nummer, 3 keine Untertitel.
Nur Standardbibliothek, Python ab 3.9.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

EXIT_FEHLER = 1
EXIT_KEINE_NUMMER = 2
EXIT_KEINE_UNTERTITEL = 3

VERSUCHE = 10
NAME_MAX = 120
ID_MUSTER = re.compile(r"[A-Za-z0-9_-]{11}")
URL_MUSTER = re.compile(r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/[^\s)\]>\"']+")
NUMMER_MUSTER = re.compile(r"^(\d+)(?=[ .]|$)")
VERBOTEN = set('/\\:*?"<>|#^[]')


class Fehler(Exception):
    """Fehler mit Meldung fuer den User und Exit-Code."""

    def __init__(self, meldung, code=EXIT_FEHLER):
        super().__init__(meldung)
        self.code = code


def video_id(url):
    """Video-ID aus einem YouTube-Link, sonst None."""
    text = url.strip()
    if "://" not in text:
        text = "https://" + text
    teile = urlparse(text)
    host = (teile.hostname or "").lower()
    for praefix in ("www.", "m."):
        if host.startswith(praefix):
            host = host[len(praefix):]
    pfad = [p for p in teile.path.split("/") if p]
    kandidat = ""
    if host == "youtu.be" and pfad:
        kandidat = pfad[0]
    elif host == "youtube.com":
        if pfad == ["watch"]:
            kandidat = parse_qs(teile.query).get("v", [""])[0]
        elif len(pfad) >= 2 and pfad[0] in ("shorts", "live"):
            kandidat = pfad[1]
    return kandidat if ID_MUSTER.fullmatch(kandidat) else None


def normale_url(vid):
    return f"https://www.youtube.com/watch?v={vid}"


def nummer(name):
    treffer = NUMMER_MUSTER.match(name)
    return int(treffer.group(1)) if treffer else None


def nn_text(zahl):
    return f"{zahl:02d}" if zahl < 100 else str(zahl)


def ordner(projekt):
    basis = Path(projekt)
    if not (basis / "@").is_dir():
        raise Fehler(f"{basis} ist kein AIOS-Projekt (kein Ordner @/).")
    return basis / "@Video", basis / "@Summary"


def lookup(projekt, url):
    vid = video_id(url)
    if vid is None:
        raise Fehler(f"Kein YouTube-Link: {url}")
    video, _ = ordner(projekt)
    if not video.is_dir():
        return
    notizen = sorted(video.glob("*.md"), key=lambda p: (nummer(p.name) or 0, p.name))
    for notiz in notizen:
        text = notiz.read_text(encoding="utf-8", errors="replace")
        if any(video_id(u) == vid for u in URL_MUSTER.findall(text)):
            nn = NUMMER_MUSTER.match(notiz.name)
            nn = nn.group(1) if nn else ""
            name = notiz.stem[len(nn):].strip()
            print(f"{notiz}\t{nn}\t{name}")
            return


def hat_json3(formate):
    return any(f.get("ext") == "json3" for f in formate or [])


def pick(info_pfad):
    info = json.loads(Path(info_pfad).read_text(encoding="utf-8"))
    manuell = {k: v for k, v in (info.get("subtitles") or {}).items() if hat_json3(v)}
    auto = {k: v for k, v in (info.get("automatic_captions") or {}).items() if hat_json3(v)}
    sprache = info.get("language") or ""
    basis = sprache.split("-")[0]

    wahl = None
    if sprache:
        for schluessel in (sprache, basis):
            if schluessel in manuell:
                wahl = (schluessel, "manuell")
                break
        if wahl is None:
            for schluessel in (f"{basis}-orig", basis):
                if schluessel in auto:
                    wahl = (schluessel, "automatisch")
                    break
    else:
        orig = [k for k in auto if k.endswith("-orig")]
        if orig:
            wahl = (orig[0], "automatisch")
        elif manuell:
            wahl = (next(iter(manuell)), "manuell")

    if wahl is None:
        raise Fehler("Dieses Video hat keine passenden Untertitel.", EXIT_KEINE_UNTERTITEL)
    titel = " ".join(str(info.get("title") or "").split())
    kanal = " ".join(str(info.get("channel") or info.get("uploader") or "").split())
    print(f"{wahl[0]}\t{wahl[1]}\t{titel}\t{kanal}")


def name_aus_titel(titel):
    zeichen = ["-" if (c in VERBOTEN or ord(c) < 32 or ord(c) == 127) else c for c in titel]
    name = " ".join("".join(zeichen).split())
    name = name[:NAME_MAX].strip()
    return name or "Video"


def belegt(nn, video, summary):
    praefix = nn + " "
    for verzeichnis in (video, summary):
        if any(p.name.startswith(praefix) for p in verzeichnis.iterdir()):
            return True
    return False


def reserve(projekt, titel):
    video, summary = ordner(projekt)
    video.mkdir(exist_ok=True)
    summary.mkdir(exist_ok=True)
    name = name_aus_titel(titel)
    zahlen = [nummer(p.name) for d in (video, summary) for p in d.iterdir()]
    kandidat = max([z for z in zahlen if z is not None], default=0) + 1

    for _ in range(VERSUCHE):
        nn = nn_text(kandidat)
        lock = video / f"{nn}.lock"
        try:
            with open(lock, "x", encoding="utf-8") as datei:
                datei.write(titel + "\n")
        except FileExistsError:
            kandidat += 1
            continue
        if belegt(nn, video, summary):
            lock.unlink(missing_ok=True)
            kandidat += 1
            continue
        print(f"{nn}\t{name}")
        return
    raise Fehler(f"Keine freie Nummer nach {VERSUCHE} Versuchen.", EXIT_KEINE_NUMMER)


def zeit(ms):
    s = int(ms) // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def transcript(json3_pfad, url, ziel):
    vid = video_id(url)
    if vid is None:
        raise Fehler(f"Kein YouTube-Link: {url}")
    daten = json.loads(Path(json3_pfad).read_text(encoding="utf-8"))
    zeilen = []
    vorher = None
    for ereignis in daten.get("events", []):
        segmente = ereignis.get("segs")
        if not segmente:
            continue
        text = " ".join("".join(s.get("utf8", "") for s in segmente).split())
        if not text or text == vorher:
            continue
        zeilen.append(f"[{zeit(ereignis.get('tStartMs', 0))}] {text}")
        vorher = text
    inhalt = f"![]({normale_url(vid)})\n\n# Transkript\n\n" + "\n".join(zeilen) + "\n"
    try:
        with open(ziel, "x", encoding="utf-8") as datei:
            datei.write(inhalt)
    except FileExistsError:
        raise Fehler(f"Datei existiert schon: {ziel}")
    print(len(zeilen))


def release(projekt, nn):
    video, _ = ordner(projekt)
    (video / f"{nn}.lock").unlink(missing_ok=True)


BEFEHLE = {
    "lookup": (lookup, 2),
    "pick": (pick, 1),
    "reserve": (reserve, 2),
    "transcript": (transcript, 3),
    "release": (release, 2),
}


def main(argv):
    if len(argv) < 2 or argv[1] not in BEFEHLE:
        print(__doc__, file=sys.stderr)
        return EXIT_FEHLER
    funktion, anzahl = BEFEHLE[argv[1]]
    argumente = argv[2:]
    if len(argumente) != anzahl:
        print(f"{argv[1]} erwartet {anzahl} Argumente.", file=sys.stderr)
        return EXIT_FEHLER
    try:
        funktion(*argumente)
    except Fehler as fehler:
        print(str(fehler), file=sys.stderr)
        return fehler.code
    except (OSError, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return EXIT_FEHLER
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
