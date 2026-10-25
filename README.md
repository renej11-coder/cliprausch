# Cliprausch @cliprauschxl

Eigenstaendiger automatischer TikTok-Kanal fuer deutsche Twitch-Momente: Gaming, Talk, IRL, Reaktionen und Comedy. Er uebernimmt den bewaehrten Buffer-Versand vom UFO-Projekt und verwendet ausschliesslich den neuen Cliprausch-Zugang. Das alte Repository wird nicht veraendert.

## Automatischer Ablauf
Vorbereitung: Quellen nach aktuellen oeffentlichen Live-Zuschauerzahlen priorisieren, aktuelle Clips nach Aufrufen pro Stunde und Live-Publikum bewerten, herunterladen und mit deutschen Wortuntertiteln rendern. H.264/AAC in 1080x1920, normalisierter Ton, kurze gut lesbare Untertitel mit hervorgehobenem aktivem Wort. Keine zusaetzliche Ueberschrift im Bild.

Schwache Transkripte oder fehlerhafte Videos werden verworfen; derselbe Vorbereitungslauf versucht bis zu drei Kandidaten. Hash-, Format-, Zeitmarken- und vollstaendige Decodierpruefung sind erforderlich. Danach werden die unveraenderten Dateien automatisch gehostet und zu Buffer geschickt. Keine manuelle Freigabe im normalen Betrieb.

Vier Slots taeglich: **12:17, 15:47, 19:17, 22:17 Europe/Berlin**. Standardabstand mindestens 150 Minuten, Tageslimit auch rollierend ueber 24 Stunden, Duplikatschutz fuer Clip-ID, Quelle, Datei und nahe Ereignisse. Zielzahl 3-5 ist in scripts/cliprausch/config.json einstellbar und setzt ausreichend geeignete Clips sowie verfuegbare Plattformen voraus.

## Laufende Rangliste ohne eigene Twitch-App
Anonyme Live-Abfrage der vorhandenen grossen Quellenliste, keine Anmeldung oder eigene Twitch-App, keine Zwei-Faktor-Aenderung, kein Kontotoken. Bei Ausfall bleibt der letzte erfolgreiche Stand erhalten. Neue Streamernamen werden nicht automatisch als lizenziert eingetragen. Eine offizielle Helix-Abfrage bleibt optional mit separaten Zugangsdaten unterstuetzt.

## Betrieb
- Secret CLIPRAUSCH_BUFFER_API_KEY nur fuer diesen Account; Ablauf 25.10.2027.
- Variable CLIPRAUSCH_ENABLED=true aktiviert den Zeitplan.
- Eigener Branch cliprausch-state speichert Vorrat, Rangliste und jeden Sendversuch vor dem Versand.
- Unklare Antworten werden abgeglichen, nicht blind erneut gesendet.
- Buffer-Sendebestaetigung plus exakte Kanal-ID, Post-ID und TikTok-Profillink ergeben confirmed_sent. Eine zusaetzliche erfolgreiche oeffentliche TikTok-Abfrage ergibt verified_public. Ein fehlgeschlagener oeffentlicher Abruf wird nicht als bestaetigt ausgegeben.
- publish-test darf genau den vom Nutzer verlangten zweiten Inbetriebnahme-Post einmal mit kuerzerem Abstand senden; der Zeitplan verwendet diesen Modus nie.

Freigaben beruhen auf dokumentierten Angaben des Kontoinhabers. Das System erteilt keine Nutzungsrechte und behauptet keine unabhaengige Lizenzpruefung. Automatische Untertitel koennen Fehler enthalten. Laufende Quellenfreigaben und Zugangsdaten bei Ablauf aktualisieren.

Details: [Betrieb und Konfiguration](scripts/cliprausch/README.md). Tests: python -m unittest discover -s tests_cliprausch -v.
