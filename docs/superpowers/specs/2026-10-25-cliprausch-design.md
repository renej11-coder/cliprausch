# Cliprausch: eigenständiger Zweitaccount

Auftrag: Gaming-/Twitch-Clips, neuer Account, besser lesbare Wortuntertitel,
keine zusätzliche Überschrift im Bild, 3–5 Veröffentlichungsplätze pro Tag.
Standard: vier Plätze, Europe/Berlin, 12:17/15:47/19:17/22:17.
Das sind Startwerte, keine nachgewiesenen optimalen Reichweitenzeiten.

Entscheidung: eigener Publisher im vorhandenen Repository statt Duplizieren
der hart codierten TikTok14-Kontoidentität. Ein neues Repository würde
zusätzliche Einrichtung erfordern; gemeinsamer veränderbarer Accountzustand
würde das bestehende Konto gefährden. Bestehende Dateien bleiben unverändert.
Buffer-GraphQL-Transport und Post-Abfrage werden wiederverwendet; Zielkonto,
Secrets, Concurrency und CAS-Zustandsbranch sind separat. Kein Fallback zum
alten Account. Ein PR aktiviert keine Veröffentlichung.

Top-50 deutscher TwitchTracker-Kanäle sind ausschließlich Discovery-Quellen.
Nutzerangabe vom 25.10.2026: große Top-100 hätten die Erlaubnis erteilt.
Das ist keine unabhängige Prüfung einzelner Nutzungsrechte. Pro Quelle ist
eine dokumentierte, gültige Freigabe einschließlich Bearbeitung, TikTok und
Audio nötig. Keine automatische Übernahme der alten Quellenfreigaben.

Medien: H.264/AAC, 1080x1920, 15–60s, ganze Szene auf weichem Hintergrund.
Untertitel aus echten Wortzeitmarken, kurze Gruppen, aktuelles Wort cyan,
keine freie Titelgenerierung. Unsichere ASR und Endfassung werden gesichtet.
Rendering ohne Servicezugänge; öffentliches Hosting erst nach Rechteprüfung.
Freigabe bindet endgültigen Dateihash und Caption; kein flag-only QA.

Versand: maximal ein Slot je Lauf, keine nachträglichen Sammeluploads,
rollierendes 24h-Limit, Mindestabstand, dauerhafte Reservierung vor POST.
Mehrdeutige POST-Antworten werden nicht wiederholt. Fremde/fehlende IDs,
unvollständige Historie oder ungeklärte Posts sperren die Übergabe.
Zeitgeber ist GitHub-Cron und damit best effort, keine garantierten 4 Posts.
Publikationszahlen zählen nur bestätigte Posts des neuen Accounts.

Offen: echte Accountanlage, verfügbares Handle, Buffer-Autorisierung,
rechtlich belegte Quellen, echte Medien-/Upload-Inbetriebnahme.
