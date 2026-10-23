# skill-video-analyse

Paket von AIbex AIOS mit dem Skill `video-analyse`, Version 0.1.0.

Aus einem YouTube-Link entstehen im Projekt zwei Dokumente, beide mit eingebettetem Video und derselben Nummer:

- `@Video/NN <Videotitel>.md`: das Transkript mit Zeitmarken `[hh:mm:ss]`;
- `@Summary/NN <Videotitel> — 5-8-Zusammenfassung.md`: eine 5-8-Zusammenfassung (Skill `5-8-zusammenfassung`).

Die Analyse läuft ohne Rückfrage, auch mehrfach parallel im selben Projekt.

## Voraussetzungen

- ein Projekt in einem mit AIbex AIOS v0.4 aktivierten Vault;
- `yt-dlp` und `python3` im `PATH`, z. B.:

```bash
pipx install yt-dlp
```

oder `python3 -m pip install --user yt-dlp` oder `brew install yt-dlp`.

## Holen

```bash
aios --fetch skill-video-analyse
```

Das holt auch `skill-5-8-zusammenfassung` und `skill-memo`. Der Skill ist ab dem nächsten Chat verfügbar.

## Aufruf

Den YouTube-Link in den Chat einfügen und dazuschreiben:

```
https://www.youtube.com/watch?v=eLDHrqKplVI Video-Analyse
```

Ebenso: „Mach mir eine Video-Analyse", „Video Analyse", „Videoanalyse".

## Grenzen

Nur YouTube-Videos mit Untertiteln; es werden nur Metadaten und Untertitel geladen, nie Video oder Audio. Keine Übersetzung.

## Lizenz

Apache-2.0, siehe `LICENSE` und `NOTICE`.
