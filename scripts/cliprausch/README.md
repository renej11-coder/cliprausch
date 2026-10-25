# Cliprausch · @cliprauschxl

Zweiter eigenständiger TikTok-Kanal für deutschsprachige Twitch-Momente:
Gaming, Talk, IRL, Reaktionen und Comedy. Keine Beschränkung auf Gameplay.

**Profilname:** Cliprausch. **Handle:** @cliprauschxl (vom Nutzer angelegt).
**Bio-Vorschlag:** `Clips. Fails. Wilde Twitch-Momente. ⚡ Auf Deutsch.`
Das bereits gesetzte violett-cyanfarbene Blitz-Profilbild passt dazu.

## Trennung vom bestehenden Account

Die bestehenden Produktionsdateien bleiben unverändert. Nur Buffer-Transport,
GraphQL-Post-Abfrage und deren bewährte Mutationsstruktur werden übernommen.
Keine veränderlichen Modulglobals, kein Fallback auf @ufo3103.

- Kanal: `6ade2a5a2f1f5ed648ca90cf`, Handle `cliprauschxl`.
- Eigener Buffer-Account; vorhandener Buffer-Connector darf ihn nicht lesen.
- GitHub-Secret: `CLIPRAUSCH_BUFFER_API_KEY`, separat von `BUFFER_API_KEY`.
- Schlüssel am 25.10.2026 angelegt, Ablauf am 25.10.2027. Nur account:read,
  posts:read und posts:write. Kein Schlüssel im Repository oder in Logs.
- Zustandsbranch: `cliprausch-state`; er enthält nur `state.json`.
- Eigene Concurrency-Gruppe; alle Zustandsschreibvorgänge verlangen die
  vorherige Dateiversion. Fehlender Zustand wird niemals automatisch geleert.
- Verbindungstest prüft Kanal, Handle, Organisation, TikTok-Dienst, Berlin,
  Verbindung, `video.publish`, Plattformbudget und vollständige Historie.

## Zeiten und tatsächlicher Durchsatz

Standard: vier tägliche Slots um **12:17, 15:47, 19:17 und 22:17 Uhr Berlin**.
`daily_target` kann auf 3 oder 5 gesetzt werden; die passenden Listen stehen in
config.json. Sommer-/Winterzeit folgt Europe/Berlin. Zeiten sind redaktionelle
Startwerte, keine belegten Reichweitenoptima. Nach zwei Wochen anhand echter
Watchtime, Completion Rate und Shares anpassen, jeweils nur einen Slot ändern.

GitHub startet alle 20 Minuten und nutzt ein 40-Minuten-Fenster je Slot.
Verspätete Starts außerhalb des Fensters holen alte Posts nicht gebündelt nach.
Maximal ein Send je Slot, mindestens 150 Minuten Abstand, Tagesbudget zusätzlich
in rollierenden 24 Stunden. Manuelle Posts auf dem neuen Account zählen mit.
Einzelne verspätete Plattformzustellungen können den folgenden Slot auslassen.
**3–5 sind ein konfiguriertes Ziel, keine garantierte Anzahl.** Freigegebene
Clips, API-Budget und Cron-Zustellung bestimmen die tatsächlich sichtbaren Posts.

Bis zu fünf Kandidaten werden verteilt über den Tag vorbereitet. Der Puffer
stoppt bei zweimal dem Tagesziel. Ein Kandidat wird noch nicht veröffentlicht:
Seine Endfassung muss freigegeben und öffentlich gehostet sein. Der Publisher
veröffentlicht anschließend automatisch aus diesem freigegebenen Vorrat.

## Quellen und Nutzungsrechte

Suchpool: deutsche TwitchTracker-Top-50, Stand 25.10.2026, aus
https://twitchtracker.com/channels/ranking/german . Die Platzierung bezieht sich
auf den TwitchTracker-Gesamtrang der letzten 30 Tage, nicht auf Live-Zuschauer.
Der Nutzer hat die Nutzung der großen Top-100 erlaubt und angegeben, dass deren
Clip-Freigaben vorliegen. config.json dokumentiert dies ausdrücklich als
**Nutzerangabe, nicht unabhängig verifizierte Lizenz**.

**Die Top-50-Liste wird nicht automatisch gescrapt.** TwitchTracker untersagt
Scraping; die dort angebotene öffentliche Basis-API liefert keine Top-50-Rangliste.
Neue Ranglisten müssen über einen erlaubten Feed oder manuell eingetragen
werden. Discovery stoppt nach sieben Tagen ohne aktualisierten Snapshot. Das
verhindert, eine veraltete Liste als „aktuell“ auszugeben.

Pro Quelle sind Erlaubnis für Bearbeitung und TikTok sowie ein Ablaufdatum
gespeichert. Die anfängliche Dreimonatsfrist ist eine interne Wiedervorlage,
keine Aussage zur rechtlichen Dauer der Erlaubnis. Pro konkretem Clip muss die
Freigabe zusätzlich Audio/Musik, Fremdvideos und sonstige Rechte berücksichtigen.
Reactions auf Filme, Serien oder Musik sind durch die Streamer-Erlaubnis allein
nicht abgedeckt. Solche Clips ablehnen oder Rechte gesondert klären. Kein
Umgehen von Zugriffssperren; nur öffentliche freigegebene Twitch-Quellen.

## Video und Qualitätskontrolle

15–60 Sekunden, 1080×1920, H.264/AAC. Ganze Quellszene vor unscharfem Hintergrund;
keine zusätzlich eingebrannte Überschrift und kein Kanal-Wasserzeichen.
Deutsche Wortzeitmarken aus faster-whisper small; kurze Gruppen mit hervorgehobenem
aktivem Wort, dunkle Kontur und Abstand zu TikToks rechter und unterer Oberfläche.
Unsichere Worterkennung wird abgelehnt; kein Ersatz durch erfundene Texte.
Vollständige Dekodierung des Videos, Audio-Lautheit normalisiert, Kontaktbild und
Transkript als Review-Artefakt. Installation und Renderprozesse erhalten keinen
Buffer-Schlüssel. Untertitelposition bei wichtigen Quell-Overlays gezielt ändern.

Die automatischen Prüfungen beweisen keine perfekte Transkriptgenauigkeit,
Humorqualität oder Nutzungsrechte. Die Freigabe bindet alle Kandidatenfelder
einschließlich Caption, Original- und Ausgabehash an einen SHA256-Wert.
Die tatsächlich gehostete MP4 wird unmittelbar vor Versand erneut gehasht.

## Betrieb

1. Workflow `Cliprausch – independent Twitch clips`, Modus **check**: überprüft
   nur die Verbindung. Keine Posts, Entwürfe oder Schedules werden erzeugt.
2. Zustand initialisieren: einmalig `cliprausch-state` mit dem Schema unten
   anlegen. Nur bei echter Erstinbetriebnahme, niemals zur Reparatur verlorener
   Historie. Normale Läufe erzeugen keinen Ersatz für fehlenden Zustand.
3. Modus **prepare**: höchstens ein Video-Kandidat wird erzeugt. Das
   sieben Tage verfügbare Actions-Artefakt enthält final.mp4, Kontaktbild,
   Transkript, qa.json und candidate.json. Noch kein TikTok-Upload.
4. Endvideo vollständig prüfen. Modus **approve** mit der Run-ID des angesehenen
   Artefakts und der Quittung unten starten. `reviewed_media_sha256` ist der
   `sha256`-Wert der tatsächlich angesehenen Enddatei aus qa.json. Audio,
   Rechte, Untertitel und Inhalt erst nach tatsächlicher Prüfung bestätigen.
5. **approve** lädt dieses Artefakt, prüft die Byte-Identität und lädt die
   freigegebene Enddatei unverändert in das Monatsrelease `cliprausch-YYYY-MM`.
   Dateinamen enthalten den Ausgabehash; existierende Assets werden nicht
   überschrieben. Der Befehl berechnet `seal(row)` über die gesamte endgültige
   Struktur und speichert die gebundene Freigabe. Kein TikTok-Post wird gesendet.
   **review** bleibt für bereits separat gehostete Enddateien verfügbar; dort
   ist der genaue finale `approved_sha256` ausdrücklich mitzugeben.
6. Nach bestandenem Verbindungstest `commissioned: true` in config.json setzen.
   Variable `CLIPRAUSCH_ENABLED=true` erlaubt den Zeitplan. Ein erster echter
   Send und die öffentliche Sichtbarkeit müssen separat geprüft werden.
   `pending` oder `sent` allein gelten nicht als nachgewiesen öffentlich.

Anfangszustand:

```json
{"version":1,"account":"cliprauschxl","channel_id":"6ade2a5a2f1f5ed648ca90cf","queue":[],"attempts":[]}
```

Review-JSON (Werte erst nach tatsächlicher Prüfung setzen):

```json
{
  "clip_id": "EXAKTE_CLIP_ID",
  "reviewed_media_sha256": "SHA256_DER_ANGESEHENEN_FINAL_MP4_AUS_QA_JSON",
  "audio_cleared": true,
  "category": "talk",
  "review": {
    "by": "NAME_DES_PRUEFERS",
    "watched_full": true,
    "subtitles_checked": true,
    "audio_checked": true,
    "frame_checked": true,
    "rights_checked": true,
    "content_checked": true
  }
}
```

Ablehnen: `{"clip_id":"EXAKTE_CLIP_ID","reject":true}`.
Abgelehnte Kandidaten werden dauerhaft von erneuter Vorbereitung ausgeschlossen.
Aktuell werden Freigaben bewusst nicht automatisch erfunden; ohne bestätigten
Vorrat bleiben Slots leer. Ein JSON-Flag allein ersetzt die tatsächliche Prüfung nicht.

## Zuverlässigkeit und Limits

Vor jedem POST steht eine dauerhaft gespeicherte Reservierung. Jede unklare
Antwort, auch Timeout/429 nach Create, behält diese Reservierung. Ein späterer
Lauf sucht ausschließlich den exakt passenden Medientitel, Kanal und
Erstellungszeitraum. **Kein blindes Retry.** Buffer sent + korrektes TikTok-Profil
+ öffentliches oEmbed oder passende öffentliche Videodaten sind erforderlich.
Ungeklärte Sends stoppen weitere Veröffentlichungen. Reconciliation reduziert
seine Frequenz bei älteren Sendungen; HTTP 429 speichert Retry-After dauerhaft.

Duplikate: Clip-ID, Quellhash, Ausgabehash und nahe Ereignisse desselben Streamers.
Die Ausschlussliste gehört dem neuen Account; Clips dürfen auf getrennten Accounts
separat redaktionell ausgewählt werden. Kein universeller Video-Fingerabdruck.
Keine Änderungen an der Ausschlussliste des alten Accounts.

Buffer-Limits sind konten-/clientabhängig und können sich ändern. Die bestehenden
Limits des alten Zugangs werden nicht als Budget des neuen Zugangs angenommen.
Die freie Queue ist begrenzt; `shareNow` nutzt keine große langfristige Buffer-Queue.
Keine eigenen TikTok-Cookies oder ungeprüfte Direct-Post-App.

Stoppen: `CLIPRAUSCH_ENABLED=false`; bereits übergebene Sends weiter abgleichen.
Nie Reservierungen löschen, um einen Stop zu umgehen. Bei fehlendem Zustand
vorherigen Branchstand restaurieren. Bei abgelaufenem Schlüssel nur das neue
Secret rotieren. Für spätere Skalierung Zustandsverdichtung mit dauerhafter
Aufbewahrung sämtlicher IDs/Hashes ergänzen; Übergröße stoppt sicher.

## Tests

```sh
python -m unittest discover -s tests_cliprausch -v
python -m unittest discover -s tests -v
python -m scripts.cliprausch.cli plan
```

Diese Offline-Tests veröffentlichen nichts. Ein synthetischer echter Render
prüft FFmpeg/libass, ersetzt aber keinen realen Twitch-/TikTok-Inbetriebnahmetest.

Quellen: [Buffer API-Limits](https://developers.buffer.com/guides/api-limits.html),
[TikTok Sharing Guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines),
[TikTok IP Policy](https://www.tiktok.com/legal/page/global/copyright-policy/en),
[TwitchTracker Basis-API](https://twitchtracker.com/api).
