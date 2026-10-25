# Cliprausch Implementation Plan

**Goal:** Getrennter, überprüfbarer Zweitaccount-Workflow ohne Änderungen am Altbetrieb.
**Architecture:** Neue Module unter scripts/cliprausch; Wiederverwendung des
bestehenden Buffer-Transports, eigener CAS-Branch und Zielkontoprüfung.
**Tech Stack:** Python 3.12, FFmpeg/libass, faster-whisper, GitHub Actions, Buffer.
**Spec:** docs/superpowers/specs/2026-10-25-cliprausch-design.md

## Global Constraints
Keine Änderungen an bestehenden Workflows, IDs, Secrets oder Zuständen.
Keine Liveposts vor Kontoautorisierung und Medien-/Rechtefreigabe.

## Tasks
- [ ] Verhaltenstests: Berliner Slots/DST, falsches Konto, Rechte, Hashbindung,
  Duplikate, verlorene POST-Antwort, Budget und CAS vor Versand.
- [ ] Konfiguration, eigenständiger Worker, Buffer-Adapter und CAS-Store.
- [ ] Dynamische ASS-Untertitel, secretfreies Rendering, Medienprüfung.
- [ ] Getrennter Actions-Workflow, Dokumentation und Profilbildkonzept.
- [ ] Gesamte Testsuite, echter synthetischer Render, Branchprüfung und Draft-PR.

## Review Focus
Falsches Konto darf niemals zum alten Account zurückfallen.
Sommer-/Winterzeit darf keine zusätzlichen Slots erzeugen.
Ein verlorener POST darf keinen zweiten Send auslösen.
Manipulierte Caption/MP4 darf alte Freigabe nicht übernehmen.
Lückenhafte Historie darf nicht als leerer Erstzustand behandelt werden.
