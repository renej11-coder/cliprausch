# Cliprausch @cliprauschxl

Eigenstaendiger Twitch-Clip-Kanal: Gaming, Talk, IRL, Reaktionen und Comedy.
Die funktionierende Buffer-Upload-Struktur vom UFO-Projekt bleibt erhalten, mit eigener Kanal-ID, Organisation, eigenem Secret und separatem Zustand. Am alten Repository wird nichts geaendert.

## Vollautomatisch
Clip-Auswahl, Download, deutsche Wortuntertitel, Rendern, technische Pruefung, Hosting und Buffer-Versand laufen ohne menschliche Freigabe. Keine eingebrannte Ueberschrift. Kurze weisse Untertitel mit dunkler Kontur und cyanfarbenem aktivem Wort; 1080x1920 H.264/AAC; Ton normalisiert. Die gesamte Datei wird beim Rendern decodiert. Hash, Format, Wortzeiten und Erkennungssicherheit werden automatisch geprueft. ASR kann Fehler enthalten; es wird keine menschliche Sichtpruefung behauptet.

Vier Slots: 12:17, 15:47, 19:17, 22:17 Europe/Berlin. daily_target in config.json erlaubt 3 bis 5. Mindestens 150 Minuten Abstand, zusaetzliches Tageslimit in rollierenden 24 Stunden. Vorbereitung fuenfmal verteilt pro Tag, Vorrat bis acht Clips. publish-now startet auf ausdruecklichen Wunsch sofort; alle Budgets und Duplikatpruefungen bleiben wirksam. GitHub startet alle 20 Minuten; Plattformverzoegerungen bleiben moeglich. Die Zielzahl setzt ausreichend geeignete Clips voraus.

Vor Versand wird eine Reservierung dauerhaft gespeichert. Nach unklaren Antworten wird nur der existierende Post abgeglichen, nie blind neu gesendet. Clips, Quell-/Dateihashes und zeitlich nahe Ereignisse werden erkannt. Buffer-Kanal und TikTok-Autor muessen exakt stimmen. Abschliessend wird die oeffentliche TikTok-Adresse geprueft. Fehlende Artifacts werden bei der Auswahl uebersprungen. CLIPRAUSCH_ENABLED=false stoppt neue Sends; Zustand niemals zur Reparatur leeren.

## Quellen und Rechte
50 deutsche Twitch-Quellen aus Snapshot 25.10.2026. Kein automatisches TwitchTracker-Scraping; veralteter Snapshot wird gemeldet. Rechte beruhen ausdruecklich auf der Erklaerung des Kontoinhabers zur erlaubten Bearbeitung und TikTok-Verwendung. Das ist keine unabhaengige Lizenzpruefung und umfasst nicht automatisch fremde Musik/Filmausschnitte. Erlaubnisse in config.json anpassen, problematische Quellen entfernen. Die konfigurierte Erlaubnis laeuft am 25.01.2027 ab und muss anhand der tatsaechlichen Freigabe aktualisiert werden.

## Zugang und Wartung
Nur neues Secret CLIPRAUSCH_BUFFER_API_KEY, Ablauf 25.10.2027. Keine Tokens in Videos, Logs oder Render-Kindprozessen. Zustand im eigenen Branch cliprausch-state. Release-Dateien sind oeffentlich und unveraenderlich benannt. Tests: python -m unittest discover -s tests_cliprausch -v. Alte manuelle review/approve-Befehle bleiben optional kompatibel; fuer den normalen Betrieb sind sie nicht erforderlich.


## Laufende Live-Rangliste
Vor jeder Clip-Vorbereitung fragt der Ablauf die offizielle Twitch-API ab: bis zu 100 deutschsprachige Livestreams, sortiert nach aktuellen Zuschauern. Quellen bleiben auf die bestehende Freigabeliste begrenzt. Live-Zuschauerzahlen werden im eigenen Zustandsbranch gespeichert; bei API-Fehlern bleibt der letzte erfolgreiche Stand erhalten. Offline-Kanaele aus der grossen Quellenliste bleiben fuer starke aktuelle Clips im Pool. Ranking-Bonus bis Faktor 3 kombiniert mit Clip-Aufrufen pro Stunde. Es wird keine TwitchTracker-Seite gescrapt.

Erforderliche neue Secrets nur im neuen Repository: CLIPRAUSCH_TWITCH_CLIENT_ID und CLIPRAUSCH_TWITCH_CLIENT_SECRET. Eine separate vertrauliche Twitch-App verwendet den Client-Credentials-Ablauf ausschliesslich fuer oeffentliche Streams, ohne Zugriff auf Chat, private Kontodaten oder Schreibaktionen. Zugriffstoken entsteht pro Vorbereitung neu; kein manuelles Erneuern des kurzfristigen Tokens. Zugangsdaten werden vor Medien-Unterprozessen aus der Umgebung entfernt. Modus ranking aktualisiert nur die Liste und zeigt die ersten 15 Prioritaetsquellen, ohne Clip-Download oder TikTok-Post. Ohne Zugangsdaten bleibt der bisherige Betrieb aktiv und meldet den fehlenden Live-Zugang.


Aktiver Zugang ohne eigene Twitch-App: Ohne Helix-Secrets liest der Ablauf anonym die oeffentlichen Live-Zuschauerzahlen der vorhandenen Quellenliste (Twitch-Webverzeichnis). Keine Anmeldung, Cookies, Zwei-Faktor-Aenderung oder Sicherheitspruefungs-Umgehung. Eine Abfrage pro Vorbereitung, kein Retry bei Sperre; dann bleibt der letzte Stand erhalten. Das ist eine Live-Sortierung innerhalb der freigegebenen grossen Quellen, keine vollstaendige dynamische Twitch-Top-100-Liste. Der inoffizielle oeffentliche Web-Endpunkt kann sich aendern.

publish-test ist ausschliesslich fuer den vom Nutzer verlangten zweiten Inbetriebnahme-Upload vorgesehen. Nur genau nach einem bereits oeffentlich bestaetigten ersten Post darf dieser manuelle Modus einmal den Mindestabstand unterschreiten. Tageslimit, Kontopruefung, Quelldateipruefung und Duplikatschutz bleiben aktiv. Der normale Zeitplan benutzt den Modus nie.


Abschlussbestaetigung: Buffer status sent, exakte Kanal-/Post-ID, plausibler Sendezeitpunkt und exakter TikTok-Profillink genuegen fuer confirmed_sent. Eine zusaetzlich erfolgreiche oeffentliche TikTok-Abfrage ergibt verified_public. Schlaegt die anonyme TikTok-Abfrage fehl, wird nicht behauptet, sie sei bestanden; public_verified bleibt false. Das verhindert, dass TikToks Abrufbeschraenkungen einen nachweislich gesendeten Buffer-Post endlos blockieren. Im Browser wurde die erste Veroeffentlichung separat angesehen.
