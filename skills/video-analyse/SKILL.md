---
name: video-analyse
version: 0.2.0
description: >
  Analysiert ein YouTube-Video: holt das Transkript mit yt-dlp (Arbeitspferd worker-yt-dlp), legt es als Video-Notiz in
  @Video/ ab und erstellt mit dem Skill 5-8-zusammenfassung eine Zusammenfassung in @Summary/,
  beide mit eingebettetem Video. Verwenden, wenn der User einen YouTube-Link mit
  „Video-Analyse", „Mach mir eine Video-Analyse", „Video Analyse" oder „Videoanalyse" schickt.
---

# Video-Analyse

Aus einem YouTube-Link entstehen zwei Dokumente im Projekt: die **Video-Notiz** `@Video/NN <Name>.md` mit dem Transkript und die **Zusammenfassung** `@Summary/NN <Name> — 5-8-Zusammenfassung.md`, beide mit eingebettetem Video und derselben Nummer `NN`.

**Leitbild:** Die Video-Analyse ist ein **Hintergrund-Job**. Der User bleibt in YouTube und startet vielleicht mehrere Analysen parallel. Deshalb: alle Prüfungen ganz am Anfang, danach **keine Rückfrage**; der Aufruf ist der Auftrag (Ausnahme R8 der Praxis *Rückfragen*). Einzige Ausnahme ist eine Dublette (V4).

Mehrere Links in einer Nachricht: nacheinander, jeder als eigener Lauf.

## Begriffe

- **Projekt:** der Arbeitsordner der Session, wenn er einen Unterordner `@/` hat; `<P>` ist sein absoluter Pfad.
- **Skript:** `python3 <Skill-Ordner>/scripts/video_analyse.py`; `<Skill-Ordner>` ist der Ordner dieses Skills („Base directory for this skill"). Immer über `python3` aufrufen, nie direkt.
- **yt-dlp:** immer `~/.aios/bin/yt-dlp`, der Weiterleiter des Arbeitspferds `worker-yt-dlp`; er nimmt die Version, die das Projekt in `lock.yaml` sperrt. Nie ein anderes `yt-dlp` aus dem `PATH`.
- **URL:** immer `https://www.youtube.com/watch?v=<Video-ID>`; **Einbettung:** `![](<URL>)`.

## 1. Vorbedingungen — in dieser Reihenfolge, beim ersten Fehlschlag aufhören

Bis hierher wird nichts angelegt.

| # | Prüfung | bei Fehlschlag |
|---|---|---|
| V1 | `<P>/@/` existiert | Meldung M1, Ende |
| V2 | Link ist YouTube: `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `youtube.com/live/…` (auch mit `www.`, `m.` und weiteren Parametern) | Meldung M2, Ende |
| V3 | `~/.aios/bin/yt-dlp --version` läuft (Exit 0) | Meldung M3, Ende. **Nach M3 endet der Lauf: keine Installation anbieten, nicht nachfragen, nichts ausführen.** |
| V4 | `Skript lookup "<P>" "<Link>"` gibt nichts aus | **einzige Nachfrage:** „Dieses Video ist schon analysiert: `<pfad>`. Soll ich aus der vorhandenen Video-Notiz eine neue Zusammenfassung machen, oder abbrechen?" — bei „neue Zusammenfassung": `NN` und `<Name>` aus der Ausgabe von `lookup`, Titel und Kanal mit Schritt 2 und `pick` holen (ohne Untertitel zu laden und ohne Schritt 4), dann weiter mit Schritt 5; bei „abbrechen": Ende |

- **M1:** „Die Video-Analyse braucht ein AIOS-Projekt (einen Ordner mit `@/`), weil sie in `@Video/` und `@Summary/` ablegt. Öffne den Chat in einem Projekt oder initialisiere diesen Ordner mit `/aios-init`, dann starte die Video-Analyse erneut."
- **M2:** „Die Video-Analyse nimmt nur YouTube-Links an (z. B. `https://www.youtube.com/watch?v=…`)."
- **M3:** „Das Paket `skill-video-analyse` ist nicht vollständig geladen: `yt-dlp` (Arbeitspferd `worker-yt-dlp`) fehlt auf diesem Rechner. Gleiche das Projekt mit `aios --fetch` ab (`/aios-fetch`), dann starte die Video-Analyse erneut." Dazu die Meldung von `~/.aios/bin/yt-dlp` in einer Zeile.

## 2. Metadaten holen

```bash
T=$(mktemp -d)
~/.aios/bin/yt-dlp -J --skip-download "<URL>" > "$T/info.json"
```

## 3. Untertitel wählen und holen

```bash
python3 <Skill-Ordner>/scripts/video_analyse.py pick "$T/info.json"
```

Ausgabe: `<schlüssel>\t<manuell|automatisch>\t<titel>\t<kanal>`. Exit 3: Meldung „Dieses Video hat keine Untertitel; eine Video-Analyse ist nicht möglich.", `rm -rf "$T"`, Ende.

```bash
~/.aios/bin/yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "<schlüssel>" --sub-format json3 -o "$T/sub.%(ext)s" "<URL>"
```

Die Datei heißt `$T/sub.<schlüssel>.json3`.

## 4. Nummer reservieren und Video-Notiz schreiben

```bash
python3 <Skill-Ordner>/scripts/video_analyse.py reserve "<P>" "<titel>"
```

Ausgabe: `NN\t<Name>`; legt `@Video/NN.lock` an. Exit 2 (keine freie Nummer): Meldung, `rm -rf "$T"`, Ende.

```bash
python3 <Skill-Ordner>/scripts/video_analyse.py transcript "$T/sub.<schlüssel>.json3" "<URL>" "<P>/@Video/NN <Name>.md"
```

**Ab hier gilt bei jedem Abbruch:** `Skript release "<P>" NN` und `rm -rf "$T"`.

## 5. Zusammenfassung erstellen

Wende den Skill **`5-8-zusammenfassung`** auf `@Video/NN <Name>.md` an, mit diesen Vorgaben:

- **Zielordner:** `@Summary/`
- **Nummer:** `NN`
- **Titel:** `<Name>`
- **nicht committen**

Danach in `@Summary/NN <Name> — 5-8-Zusammenfassung.md`:

1. im Header-Block direkt nach der Zeile `**Status:** …` einfügen:
   - `**Betrifft:** Video von <kanal>, <URL>`
   - ``**Quelle:** `@Video/NN <Name>.md` (automatische Untertitel von YouTube)`` — bei `manuell`: „(Untertitel von YouTube)"
2. direkt nach dem Header-Block, vor `## 1)`: eine Leerzeile, die Einbettung, eine Leerzeile.

Ergebnis:

```markdown
# <Titel> — 5-8-Zusammenfassung

**Datum:** <heute>
**Status:** Zusammenfassung
**Betrifft:** Video von <kanal>, <URL>
**Quelle:** `@Video/NN <Name>.md` (automatische Untertitel von YouTube)

![](<URL>)

## 1) …
```

**Scheitert Schritt 5:** Die Video-Notiz bleibt und wird in Schritt 6 allein committet; melde ihren Pfad und dass die Zusammenfassung fehlt (sie lässt sich mit einem neuen Aufruf über V4 nachholen). Liegt `@Summary/NN …` schon vor, wird nichts überschrieben; melde das.

## 6. Abschluss

```bash
python3 <Skill-Ordner>/scripts/video_analyse.py release "<P>" NN
rm -rf "$T"
```

Ist `<P>` ein Git-Repo, **nur die eigenen Pfade** committen, nie `git add -A`:

```bash
git -C "<P>" add -- "@Video/NN <Name>.md" "@Summary/NN <Name> — 5-8-Zusammenfassung.md"
git -C "<P>" commit -m "Video-Analyse NN: <titel>" -- "@Video/NN <Name>.md" "@Summary/NN <Name> — 5-8-Zusammenfassung.md"
```

Scheitert der Commit an einem Lock von Git (`index.lock`), bis zu drei Mal nach kurzer Pause wiederholen.

Melde beide Pfade als Markdown-Link.

## Grenzen

- Keine Rückfrage außer V4.
- Nur YouTube; nie Video oder Audio laden (immer `--skip-download`).
- Nichts installieren und keine Installation anbieten; `yt-dlp` kommt mit dem Paket (M3 verweist nur auf `aios --fetch`). Die Meldung M3 ist das Ende des Laufs.
- Keine Übersetzung; das Transkript bleibt in der Originalsprache.
- Nur in `@Video/`, `@Summary/` und `$T` schreiben; Lock-Dateien nie committen.
- Ein nach einem harten Abbruch liegengebliebenes `@Video/NN.lock` darf der User von Hand löschen.
- Schlägt `yt-dlp` fehl, dessen Meldung weitergeben, aufräumen, Ende. Die JS-Runtime `deno` kommt mit `worker-deno`, einer Abhängigkeit von `worker-yt-dlp`.
