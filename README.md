# Im Zweifel Goethe

Instagram-Satirebot (@im.zweifel.goethe): Jeden Tag ein falsch zugeschriebenes Zitat mit Bezug
zu einer echten, aktuellen Nachricht, als Reel. Eigenständige Kopie des englischen Bots
„Citation Needed“ (Repository `realbeardedman/witz-bot`), der unabhängig davon weiterläuft.

## Ablauf eines Laufs

1. **Zeitfenster prüfen** (`schedule_plan.py`): 07:17 oder 19:17 Uhr Berliner Zeit (Crons mit
   `timezone: Europe/Berlin`, von GitHub seit März 2026 unterstützt). Im Modus `test` wechseln Morgen und
   Abend täglich; höchstens ein Beitrag (auch ein reservierter) pro Berliner Kalendertag.
2. **Schlagzeilen** aus Google News Deutschland (`hl=de`, `gl=DE`), höchstens 48 Stunden alt,
   Themen rotieren (Wirtschaft, Arbeit, Bürokratie, Technik & KI, Konsum, Sport & Kultur, Kurioses).
   Unglücke, Gewalt, Krankheit u. Ä. werden per Sperrliste aussortiert, bereits behandelte Links übersprungen.
3. **Autor** (Gemini, Ausweich: Cloudflare): sechs Varianten, Zitat ≤ 22 Wörter, Urheber ≤ 8 Wörter.
4. **Schlussredaktion** (zweiter, unabhängiger Aufruf): Sicherheits- und Nachrichtenbezugsprüfung,
   Note nach fester Skala. Veröffentlicht wird nur ab 8/10, sonst kein Beitrag. Bis zu sieben Themen pro Lauf.
   Danach harte Dublettenprüfung: kein Zitat zweimal, kein Urheber zweimal innerhalb von 30 Beiträgen.
5. **Reel** (1080 × 1920, H.264, stille Tonspur): Hook → Zitat mit „Wer hat's gesagt?“ → Urheber als Pointe
   → „Schick das …“. Wortlogo „IM ZWEIFEL / GOETHE.“ mit „SATIRE / ERFUNDENES ZITAT“, Schlagzeile und Quelle
   oben, Satirehinweis in der Caption (die Caption verrät die Pointe nicht).
6. **Veröffentlichung** über die Instagram-API (Meta Unified Login, direkter Video-Upload).
   Vorher: Prüfung von Repository und tatsächlichem Instagram-Konto, dann **Reservierung** des Beitrags im
   Verlauf (wird vor dem Upload gepusht; scheitert der Push, wird nichts gepostet). Bleibt ein Eintrag mit
   `"status": "reserved"` stehen, zuerst im Instagram-Konto nachsehen; es gibt keinen automatischen zweiten Versuch.

## Regeln für Urheber

Erlaubt: historische Personen, die seit mindestens 50 Jahren tot sind; Figuren aus Märchen, Sagen,
Mythologie, Bibel und gemeinfreier klassischer Literatur; ab und zu Goethe selbst.
Ausgeschlossen: lebende Personen, Privatpersonen, kürzer als 50 Jahre Verstorbene, Täter und
Symbolfiguren von Diktatur, Völkermord oder Terror, Figuren aus geschützten modernen Werken.

## Einrichtung (Kontoinhaber)

1. **Meta:** Instagram-Konto @im.zweifel.goethe (professionelles Konto) im Business-Portfolio „Deadpan Desk“
   hinzufügen und dem Systemnutzer `deadpan-bot` zuweisen (volle Kontrolle). Token mit `instagram_basic`,
   `instagram_content_publish` (und ggf. `business_management`), Ablauf „Nie“.
2. **Secrets** (Settings → Secrets and variables → Actions → Secrets):
   `GEMINI_API_KEY`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `IG_ACCESS_TOKEN`, später `IG_USER_ID`.
3. **Variables** (gleiche Seite, Reiter „Variables“): `IG_EXPECTED_USERNAME` = `im.zweifel.goethe`,
   `AUTO_PUBLISH` = `false`.
4. **Settings → Actions → General → Workflow permissions:** Read and write.
5. Actions → Im Zweifel Goethe → Run workflow → `verbindung_pruefen`; angezeigte ID als Secret `IG_USER_ID`.
6. `testlauf` (postet nicht) mehrmals ausführen, Reel unter „Artifacts“ ansehen.
7. Nach Freigabe: einmal `posten` von Hand, dann `AUTO_PUBLISH` auf `true` setzen.

## Modi

| Modus | Wirkung |
|---|---|
| `testlauf` | 1 Reel erzeugen, als Download bereitstellen, nichts posten |
| `posten` | 1 Reel erzeugen und veröffentlichen (geplant nur bei `AUTO_PUBLISH=true`) |
| `startpaket` | mehrere Reels (Standard 3) in `queue/` ablegen, nichts posten |
| `warteschlange_posten` | alle Reels aus `queue/` veröffentlichen |
| `wochenrueckblick_test` / `wochenrueckblick` | Karussell der besten Zitate (nur manuell) |
| `verbindung_pruefen` | Token, zugewiesene Konten und Veröffentlichungsrecht prüfen |

Hinweis: `posten` erzeugt ein neues Zitat und verwendet nicht das zuvor im Testlauf geprüfte.
Wer genau ein geprüftes Reel posten will, nutzt `startpaket` → durchsehen → `warteschlange_posten`.

## Postingzeit-Test

`posting_mode` in `config.json`: `test` (täglich wechselnd), `morning` oder `evening`.
Plan: vier Wochen Test, danach je Reel nach 72 Stunden vergleichen (erreichte Konten, Weiterleitungen,
durchschnittliche Wiedergabedauer, neue Follower) und den besseren Slot fest einstellen.
Automatische Insights-Auswertung ist nicht eingebaut. GitHub startet geplante Läufe teils mit Verzögerung.

## Anpassen (`config.json`)

| Feld | Wirkung |
|---|---|
| `handle`, `wordmark`, `label` | Handle, Wortlogo und Satirekennzeichnung im Reel |
| `topics`, `formats` | Themenfelder, Suchbegriffe, Hashtags, Zitat-Formate |
| `design` | Farben (Tintenblau, Papier, Gold, Siegelrot) |
| `min_score` | Mindestnote der Schlussredaktion (8) |
| `posting_mode`, `slots` | Zeitfenster-Test und Uhrzeiten (Berliner Stunde) |
| `blocklist` | Begriffe, bei denen eine Schlagzeile verworfen wird |

## Tests

`python -m unittest discover -s tests -v` (19 Tests, ohne echte API-Aufrufe; laufen auch in jedem Workflow).

## Fehlerbehebung

| Meldung | Lösung |
|---|---|
| `Falsches oder nicht erreichbares Instagram-Konto` | `IG_USER_ID`/Token gehören nicht zu @im.zweifel.goethe; `verbindung_pruefen` ausführen |
| `Video-Upload fehlgeschlagen` | in `config.json` `"upload_mode": "url"` setzen (Repository ist öffentlich) |
| `Container-Fehler 190` | Token ungültig: beim Systemnutzer neu erzeugen, Secret ersetzen |
| `Kein Post: …` im Schritt „Zeitfenster prüfen“ | kein Fehler: falsches Zeitfenster oder heute schon gepostet |
| `Heute kein Witz, der die Prüfung besteht` | kein Fehler: Qualität geht vor täglicher Veröffentlichung |

Schriften: Inter (SIL Open Font License, siehe `fonts/LICENSE-Inter.txt`).

## Übernommen aus dem ChatGPT-Entwurf (v1.1)

Wortlogo, Reservierung vor dem Upload, harte Dublettenprüfung, Hinweis „Schlagzeilen sind Daten“ in den
Prompts, gekürzte Instagram-Fehlermeldungen, Crons mit Zeitzone. Nicht übernommen: Caption mit Zitat und
Urheber in der ersten Zeile (verrät die Pointe), eigenes Politik-Thema (Reichweitenbremse bei Instagram),
statisches Zwei-Bild-Video ohne Hook und Aufruf zum Weiterschicken.
