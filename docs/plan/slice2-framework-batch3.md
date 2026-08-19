# Slice 2, Framework-Batch 3 → `v0.5.0`

**Repo:** `cosmo-suite` · **Branch:** neu, `slice2-framework-batch3` off `main`
**Vorgänger:** `v0.4.1` (beide Apps laufen darauf) · **Erstellt:** 2026-08-19

---

## 0. Zweck und Reihenfolge

Slice 1 und 1b haben rund 4.600 Zeilen Infrastruktur aus beiden Apps ins Framework
geholt. Was noch lokal liegt, ist keine Bequemlichkeitsarbeit mehr, sondern durch
**fehlende Framework-Nahtstellen blockiert**:

| Modul | cosmopolitan | cosmonaut | blockiert durch |
|---|---|---|---|
| `error_handling` | 279 Z. | 196 Z. | `on_unhandled`-Hook fehlt (§2) |
| `files_route` | 97 Z. | 131 Z. | `cosmo_suite.files_route` ruft den konkreten `Job` (§3) |
| `db_manager` / `postgres_manager` | 1241 Z. | 448 Z. | keine gemeinsame `Base` (§6) |
| `layouts` / `layout` | 288 Z. | 1076 Z. | Wrapper-Naht unvollständig (§4) |
| `job` | 807 Z. | 726 Z. | kein `BaseJob`-Contract (§3) |

Dieser Batch baut die Nahtstellen. **Er ändert in den Apps nichts** und geht deren
Arbeit voraus. Danach wird getaggt und für die Dauer von Slice 2 **eingefroren**.

**Freeze-Regel:** Braucht ein App-Agent während Slice 2 eine Framework-Änderung, ist das
ein eigener MR hier, ein neuer Tag, und **beide** Apps re-pinnen. Keine stillen Edits am
Framework, während App-Agenten laufen. Das hat in Slice 1 funktioniert und war der
Grund, dass zwei Agenten parallel arbeiten konnten.

---

## 0b. Was vor dem Start geklärt ist, und was der Agent selbst entscheidet

Damit niemand mitten im Batch hängt:

| Punkt | Status |
|---|---|
| §2 `on_unhandled`-Signatur | festgelegt in `cosmo-core-package-boundary.md` §3(d) |
| §3 `BaseJob`-Vertrag | festgelegt in §3(e); `time_to_live` mit Deprecated-Alias, siehe §3 |
| §3 `FileValidationError`-Kollision | **nicht Sache dieses Batches.** Das Framework definiert die Klasse weiter; die Auflösung ist app-seitig und gehört in cosmopolitans Slice-2-Plan |
| §4 Zugangspunkt für `wrapper_class` | **Agent entscheidet.** Empfehlung unten in §4 |
| §6 Schnittmenge der `JobTable` | **geklärt, siehe §6.** Keine Rückfrage nötig |

**Release-Mechanik:** cosmo-suite hat **keinen** Release-Job, weil dort `SSH_PRIVATE_KEY`
in der CI fehlt. `version = "0.5.0"` und der Tag sind hier ein Handgriff von Hand, anders
als in den beiden Apps.

**Dieses Dokument ist ungetrackt.** Wer auf einem frischen Clone arbeitet, hat es nicht.

## 1. Vorarbeit, die gilt, und was daran veraltet ist

[`cosmo-core-package-boundary.md`](cosmo-core-package-boundary.md) §3(d) und §3(e)
spezifizieren **beide Kern-Signaturen dieses Batches schon**. Nicht neu erfinden, dort
nachlesen. Ebenso §2 für die `error_handling`-API-Skizze.

**Was an dem Dokument veraltet ist** (es ist vom 2026-06-29, also vor der eigentlichen
Extraktion):

- **Namen:** es sagt durchweg `cosmo_core` und `cosmo-template`. Heute heißt es
  `cosmo_suite`, und die Referenzdomäne ist `examples/csv_profiler/`.
- **Schon erledigt, nicht nochmal anfassen:** §3(f) Env-Var-Standardisierung
  (`POSTGRES_DB`, `FLASK_DEBUG`, `PORT`) ist in Slice 1 durch. Der `LogTable`-Lift aus
  §3(g) ist durch. `ExcludeSubmodulesFilter` mit Ctor-Argument ist als
  `excluded_packages` in Batch 2 durch. `level_badge` tolerant ist durch.
- **Es kennt drei Befunde nicht**, die erst im Betrieb aufgefallen sind: §4, §5 und §6
  unten. Die stehen in keinem Altdokument.

---

## 2. `handle_error(on_unhandled=...)`

Heute: `cosmo_suite/error_handling.py:172` ist `def handle_error(error):` und loggt nur.

Beide Apps mailen bei unbehandelten Fehlern an `MAINTAINER_EMAIL`
(`cosmopolitan_app/error_handling.py:253`, `cosmonaut_app/error_handling.py:169`).
Solange der Hook fehlt, kann keine der beiden ihr `error_handling` aufgeben, denn ein
Wechsel würde die Maintainer-Mails **still** abschalten. Kein Importfehler, kein
Testfehlschlag, nur ausbleibende Mails.

Signatur wie in §3(d) des Altdokuments festgelegt:

```python
def handle_error(error, *, on_unhandled: Callable[[Exception], None] | None = None) -> None:
```

Zwei Auflagen:

- **`error_handling` darf `email_service` nicht importieren.** Der Versand bleibt
  app-seitig, das Framework ruft nur den übergebenen Callable. Andernfalls entsteht ein
  Zyklus und das Framework zöge Mailkonfiguration in seine Abhängigkeiten.
- **Keyword-only**, damit bestehende `handle_error(e)`-Aufrufe unverändert weiterlaufen.
  Der Batch soll `v0.4.1` nicht brechen.

Dazu die Kollision auflösen, die im Slice-1-Handoff schon benannt war:
`FileValidationError` existiert im Framework **und** kommt in cosmopolitan aus
`soil_moisture_prediction.input_file_parser`. Entscheidung hier treffen und
dokumentieren: entweder fängt die App beide, oder der Upload-Pfad wrappt die
SMP-Exception in die Framework-Exception. Nicht stillschweigend überschreiben, sonst
greift das `except` im Upload-Callback nicht mehr.

---

## 3. `BaseJob`-Contract, der Schlüsselposten

Das ist der Posten mit der größten Hebelwirkung: `cosmo_suite/files_route.py:13` macht
`from cosmo_suite.job import Job`, also den **konkreten** Framework-Job. Deshalb hält
cosmopolitan 97 und cosmonaut 131 Zeilen `files_route` lokal, und beide Docstrings sagen
das inzwischen selbst.

Heute hat `cosmo_suite/job.py` vier Klassenattribute als Naht (`config_model`,
`file_validator`, `submit_handler`, `app_version`), aber keinen abstrakten Vertrag. Die
Apps können ihn deshalb nicht erfüllen, ohne den ganzen konkreten `Job` zu übernehmen.

Vertrag wie in §3(e) festgelegt: `job_id`, `save`, `delete`, `submit`, `time_to_live`.
Konstruktion und Speicherung bleiben app-seitig. **Log-Refresh ist nicht abstrakt.**

Dazu `submit_job(task_name, job_id, queue, *, track_task_name=False, **opts)`: es nimmt
eine schlichte `job_id`, App-Wrapper ziehen sie heraus (`job.job_id` gegen
`job.model.job_id`). Cosmonauts Redis-Registrierung des Tasknamens ist
`track_task_name=True`.

**Gemessene Falle beim Namen.** Das Altdokument verlangt die korrekte Schreibweise
`time_to_live`. Der Tippfehler `time_to_life` steckt aber im **Framework selbst**
(`cosmo_suite/job.py`) und in cosmopolitan (`job.py`, plus **fünf** Stellen in
`pages/submission.py`). Cosmonaut hat ihn nicht. Ein Rename ist also eine Breaking
Change für cosmopolitan über sechs Call-Sites.

Empfehlung: `time_to_live` als Vertragsnamen einführen und `time_to_life` im Framework
als deprecated Alias behalten, das auf den neuen Namen delegiert. Dann adoptiert
cosmopolitan ohne Bruch und räumt seine sechs Stellen auf, wann es passt. Das ist genau
das Muster, das das Altdokument als Design-Invariante nennt: additive Naht statt
Bruch.

---

## 4. `wrapper_class` ist noch offen, und zwar anders als gedacht

Batch 2 hat `page_container_column_layout(content, main_content_id=..., wrapper_class=None)`
ergänzt. Cosmonaut hat gemeldet, dass das nicht hilft, und der Befund ist bestätigt:

**Die drei Framework-Seiten rufen die Funktion selbst auf, ohne den Parameter
weiterzugeben** (`pages/job_management.py:102`, `pages/logs.py:242`,
`pages/worker_management.py:575`). Ein Consumer, der eine Marker-Klasse braucht, hat
keinen Weg, sie dort hineinzureichen. Deshalb musste cosmonaut sein `style.css`
zusätzlich auf `#main-content-container` keyen.

Der Parameter existiert also, nur ohne Zugang. Zu entscheiden ist, wo der Zugang liegt.
Wichtig dabei: die Seiten registrieren sich zur Importzeit, ein Konfigurationspunkt muss
also **vor** dem Import der Seiten gesetzt werden können, so wie die `Job`-Nahtstellen.

**Empfehlung:** ein Modul-Level-Default im Framework, den eine App vor dem Seiten-Import
setzt, und den die drei Seiten beim Aufruf durchreichen. Das folgt dem Muster, das im
Repo schon existiert (die vier `Job`-Klassenattribute), statt ein zweites Muster
einzuführen. Ein Argument an den Layout-Funktionen wäre die Alternative, hilft aber
nicht: die Seiten bauen ihr `layout` selbst, ein Consumer ruft sie nicht auf. Wenn dem
Agenten beim Bauen ein besserer Schnitt auffällt, darf er ihn nehmen und begründen.

Abnahmekriterium ist nicht "Parameter existiert", sondern: cosmonaut kann seine
CSS-Umgehung zurücknehmen.

---

## 5. Die Duplicate-Callback-Falle dokumentieren

Cosmopolitan hat in Slice 1b Folgendes gefunden, und cosmonaut läuft in Slice 2 hinein:

Importiert eine App eine Framework-Seite, kommt `cosmo_suite.layouts` mit und
registriert dort einen Callback auf einer ID, die die App schon belegt hatte. Dash
bricht daraufhin die **gesamte** Callback-Registry ab, und das Symptom erscheint auf
einer ganz anderen Seite als die Ursache. Cosmopolitan hat es gelöst, indem der lokale
Callback entfiel.

Cosmonaut ist bisher davongekommen, weil es `cosmo_suite.layouts.app_layout()` gar nicht
aufruft. In Slice 2 wird es das tun.

Das ist der **dritte** Fall desselben Musters, nach `ObjectStorageError` (gleicher Name,
andere Klasse, `except` greift still nicht mehr) und `WEB_WORK_DIR` (relativer Pfad,
`send_from_directory` 404t jedes Bild). Alle drei: kein Importfehler, kein
Testfehlschlag, Symptom weit weg von der Ursache.

Beim dritten Fall gehört daraus eine Regel ins Framework, nicht eine vierte
Einzelfundstelle. Nach `docs/conventions/`, und aus `README.md` verlinkt: **was ein
Consumer beim Import einer Framework-Seite mitübernimmt, und was daran still
fehlschlagen kann.**

---

## 6. Gemeinsame `Base`: hier ist eine Entscheidung zu treffen, keine Implementierung

Seit Slice 1 laufen in **beiden** Apps zwei SQLAlchemy-Engines im selben Prozess: die der
App und die des Frameworks (`cosmo_suite/db_manager.py:98` gegen das lokale Pendant), mit
zwei getrennten `Base`-Registries, die beide `LogTable` auf `logs` und `JobTable` auf
`jobs` mappen, gegen dieselbe Datenbank.

Es funktioniert, verifiziert an laufenden Apps: der Framework-`DbManager` bedient nur die
Log-Queries der Framework-Seiten. Aber es sind zwei Connection-Pools und zwei Mapper für
dieselben Tabellen.

Das Altdokument §3(g) hat dafür eine Antwort, die noch trägt: Framework-`JobTable` ist ein
**ORM-Spiegel** der strikten Schnittmenge (`job_id, submitted, status, version`, plus
`start_date` wo vorhanden), die autoritative DDL bleibt pro App in `init.sql`, und
app-spezifische Spalten und Tabellen bleiben app-seitig auf der Framework-`Base`.

**Was dieser Batch tut:** die Framework-`Base` als expliziten, dokumentierten
Exportpunkt bereitstellen und die Schnittmenge festschreiben. **Was er nicht tut:** die
Apps umhängen, das ist deren Slice-2-Arbeit.

**Die Abweichung, die die Schnittmenge bestimmt, ist gemessen (2026-08-19).**
Cosmopolitans `JobTable` (`postgres_manager.py:1137`) mappt neun Spalten und hat
zusätzlich `prepared_input`. Sein `docker/init.sql` führt zwei weitere, `email` und
`celery_task_id`, die im ORM **nicht** vorkommen.

Diese zwei sind **toter Schema-Ballast**: `email` wird nirgends gelesen oder geschrieben,
`celery_task_id` existiert nur als In-Memory-Attribut (`job.py:205` deklariert,
`job.py:270` auf `None` gesetzt) ohne ORM-Mapping, und es gibt kein rohes SQL gegen
`jobs`. Sie sind also für die Schnittmenge irrelevant und dürfen ignoriert werden.

Damit bleibt als Schnittmenge genau das, was das Altdokument vorschlägt:
`job_id, start_date, input_data, submitted, notified_end, logs, status, version`.
Cosmopolitans `prepared_input` und alle cosmonaut-eigenen Tabellen bleiben app-seitig auf
der Framework-`Base`.

---

## 7. Ausdrücklich NICHT in diesem Batch

- **`DomainPlugin`-Protokoll, Plugin-Registry, Branding-Layer** aus
  [`framework-generalization.md`](framework-generalization.md). Davon ist nichts
  implementiert, und nichts davon braucht das Paper. Das Dokument beschreibt außerdem
  `cosmo_core`-Namen und eine Repo-Struktur, die es nicht mehr gibt.
- **Die Apps anfassen.** Dieser Batch baut nur Nahtstellen.
- **`layouts` vereinheitlichen.** Cosmonauts `layout.py` hat 1076 Zeilen, überwiegend
  Kartenlayout. Höchstes Risiko, kleinster Ertrag, und es kommt in der App-Reihenfolge
  ganz zuletzt.
- **`ruff format` repo-weit.** In cosmonaut sind 27 vorbestehende Fehlschläge; ein
  Format-Commit würde unbeteiligte Dateien anfassen und jede Belegzahl verwässern.

---

## 8. Verifikation (Definition of Done)

Das Framework hat außer `test/test_html_id_enforcement.py` keine eigene Suite. Der
einzige echte Prüfstand ist das Beispiel, und es ist ein guter: eine dritte Domäne ohne
Geo-Abhängigkeiten, mit e2e.

```bash
cd examples/csv_profiler && ./run_pytest.sh      # muss grün bleiben
cd /home/trinkle/git/cosmo-suite
uv run ruff format --check cosmo_suite test
uv run ruff check cosmo_suite test
grep -rnE --include='*.py' 'csv_profiler|ProfileConfig|computation_module|validate_csv|profile_csv|CSV_UPLOAD' cosmo_suite/   # muss leer sein
```

Zusätzlich, weil dieser Batch Verträge einführt statt Code zu verschieben:

- **`csv_profiler` muss den neuen `BaseJob`-Vertrag erfüllen**, nicht nur weiterlaufen.
  Wenn die Referenzdomäne ihn nicht sauber erfüllen kann, ist der Vertrag falsch
  geschnitten, und das merkt man hier billiger als in zwei Apps.
- **Ein Test für den `on_unhandled`-Hook:** wird der Callable gerufen, und läuft
  `handle_error(e)` ohne ihn unverändert weiter.
- **Rückwärtskompatibilität gegen `v0.4.1` bewusst prüfen.** Beide Apps laufen darauf.
  Jede Änderung hier ist additiv oder bekommt einen Alias (§3).

Fertig heißt: Beispielsuite grün, `ruff` sauber, Domain-free-Gate leer,
`version = "0.5.0"`, Tag `v0.5.0` gepusht, und die Konventionsdatei aus §5 existiert.

**Danach** kommen die beiden App-Pläne. Die schreibe ich erst, wenn `v0.5.0` steht, weil
sie auf den tatsächlichen Signaturen aufsetzen sollen und nicht auf geplanten.

---

## 9. Konventionen

`CLAUDE.md` gilt: keine `dict.get()`, kein bare `except Exception`, keine Inline-Imports,
HTML-IDs nur aus `cosmo_suite/constants/html_ids.py`, kein Inline-CSS. Abweichung ist
erlaubt, mit Kommentar, der sie begründet.

Zwei Muster aus diesem Repo, die hier besonders zählen: Nahtstellen sind
Klassenattribute, die **vor** dem ersten Gebrauch gesetzt werden (siehe die vier
`Job`-Attribute und `examples/csv_profiler/csv_profiler/app.py`), und Callbacks werden
zur Importzeit verdrahtet, weshalb §4 und §5 zusammengehören.
