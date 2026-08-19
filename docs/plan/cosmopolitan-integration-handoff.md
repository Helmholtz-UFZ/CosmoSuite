> ⚠️ **ÜBERHOLT (2026-08-04).** Gültiger Stand ist
> `../cosmopolitan/docs/plan/cosmo-suite-integration.md`. Die gemessenen Modul-Diffs hier
> sind korrekt und dort übernommen; drei Verdikte waren zu optimistisch (Dependency-Auth,
> `logger.py`, `error_handling.py` — die beiden Framework-Seams existieren noch nicht) und
> sind dort korrigiert. Nur noch als Beleg aufbewahrt.

# Handoff: cosmo-suite in COSMOPOLITAN integrieren

**Erstellt:** 2026-08-04 · **Adressat:** der Coding-Agent, der in `../cosmopolitan` arbeitet
**Status:** Framework ist getaggt und bereit; Cosmopolitan ist der *erste* Consumer.

Alle Zahlen unten sind gemessen (Diff der realen Trees am 2026-08-04), nicht geschätzt.
Import-Präfixe wurden für den Vergleich normalisiert (`cosmo_suite` ↔ `cosmopolitan_app`),
d.h. "0 Diff-Zeilen" heißt: identisch bis auf das Präfix.

---

## 0. Das Wichtigste in drei Sätzen

Cosmopolitan ist der einfache Fall: Die Env-Var-Namen stimmen bereits **exakt** überein,
42 gemeinsame HTML-ID-Konstanten haben **identische Namen und Werte**, und das
`Job`-Objekt benutzt schon dasselbe `self.model`-Pydantic-Muster wie das Framework.
Drei Module sind byte-identisch und können sofort gelöscht werden. Die Arbeit steckt in
`db_manager`/`postgres_manager` (Klassenname + eigene Tabellen auf einer gemeinsamen
`Base`) und in `job.py`/`layouts.py` (Domänenlogik, die drin bleibt).

---

## 1. Dependency-Pin

```toml
# cosmopolitan/pyproject.toml → [project].dependencies
"cosmo-suite @ git+https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite@v0.2.0",
```

- **Tag `v0.2.0`** → Commit `56c8e33` ("Rename to cosmo-suite"). Import-Name: `cosmo_suite`.
- **Nicht `v0.1.0`/`0.1.0` verwenden** — die liegen *vor* dem Rename und liefern noch
  `cosmo_framework`.
- Auth im CI über `CI_JOB_TOKEN`, lokal über SSH. `uv lock` pinnt den Commit-Hash.
- Framework-Deps sind bewusst weite Ranges (`dash>=3.0.4,<4`, `sqlalchemy>=2,<3`,
  `celery[redis]>=5.3,<6`, `pydantic>=2,<3`, `psycopg2>=2.9.10,<3`, `coolname`, `gunicorn`,
  `python-dotenv`) — kollidiert nicht mit Cosmopolitans eigenen Pins.
- **Achtung `dotenv`:** Cosmopolitan hat `dotenv>=0.9.9,<0.10` (das Fremdpaket), das
  Framework `python-dotenv>=1,<2`. Beide liefern das Modul `dotenv`. Beim ersten
  `uv sync` prüfen, welches gewinnt; Empfehlung: in Cosmopolitan auf `python-dotenv`
  wechseln und `dotenv` streichen.
- Für den Dev-Loop existiert im Framework-Repo das Muster
  `examples/csv_profiler/docker-compose.local_pkg.yml` (Bind-Mount des Framework-Trees
  + `PYTHONPATH`) — für Cosmopolitans PYTHONPATH-Prepend-Mechanik adaptieren.

---

## 2. Modul-für-Modul: gemessener Zustand

| Modul | Diff-Zeilen | Verdikt |
|---|---|---|
| `object_storage_manager.py` | **0** | **Löschen**, ersetzen durch `cosmo_suite.object_storage_manager` |
| `logs_table.py` | **0** | **Löschen**, ersetzen durch `cosmo_suite.logs_table` |
| `files_route.py` | **2** | Fast identisch — Framework setzt `id=DOWNLOAD_BUTTON_SHARED_ID` am Download-Button (Cosmopolitan hat den Constant noch nicht) |
| `logger.py` | **7** | Übernehmen; 3 Divergenzen, siehe §4.1 |
| `config.py` | **21** | Framework-Basis importieren, Domänen-Extras anhängen (§3) |
| `celery_app.py` | **23** | Domänen-Manifest — Framework liefert nur die App, Cosmopolitan registriert seine Tasks |
| `celery_config.py` | **25** | `BaseCeleryConfig` subclassen, eigene `task_routes`/`beat_schedule` setzen |
| `pages/logs.py` | **22** | Framework-Page verwenden |
| `pages/job_management.py` | **57** | Framework-Page verwenden, Abweichungen prüfen |
| `pages/worker_management.py` | **86** | Framework-Page verwenden — ID-Namen unterscheiden sich (§4.2) |
| `error_handling.py` | **93** | Struktur identisch; Cosmopolitan-Extras bleiben (§4.3) |
| `background_job_manager.py` | **212** | `BackgroundJobManager` erben/nutzen; `submit_computation_job` bleibt domänenseitig (§4.4) |
| `layouts.py` | **249** | Teilweise — Navbar/Branding ist domänenspezifisch (§4.5) |
| `pydantic_models.py` | **196** | `ModelWebsite` von `BaseJobConfig` erben lassen (§4.6) |
| `postgres_manager.py` | vs. `db_manager.py` | Erste 18 Methoden deckungsgleich, ab `_extract_date` (Zeile 416) reine CRNS-Domäne (§4.7) |
| `job.py` | 637 | Bleibt domänenseitig; Seams injizieren (§4.8) |
| `doc_generator`, `email_service`, `form_template_factory`, `map_utils`, `screenshot_generator`, `timeio_*`, `utils` | — | Reine Domäne, unangetastet |

---

## 3. Env-Vars: kein Gate, alles passt

Das Framework liest in [`cosmo_suite/config.py`](../../cosmo_suite/config.py) **19 Variablen
zur Importzeit** und wirft `ValueError`, sobald eine fehlt. Verifiziert: Cosmopolitan
verwendet **exakt dieselben Namen** (`FLASK_PORT`, `FLASK_DEBUG`, `POSTGRES_DB`,
`POSTGRES_HOST_NAME`, `REDIS_DB`, `REDIS_PASSWORD`, `OBJECT_STORAGE_*`, `WEB_*`). Kein
Rename nötig. (Nur Cosmonaut divergiert mit `POSTGRES_NAME`/`DEBUG` — dessen Problem,
nicht deins.)

Cosmopolitans `config.py` wird zu:

```python
from cosmo_suite.config import *  # oder explizit die genutzten Namen
from cosmo_suite.config import getenv

TILESERVER_URL = getenv("TILESERVER_URL")
EMAIL_SERVER = getenv("EMAIL_SERVER")
EMAIL_PORT = getenv("EMAIL_PORT")
EMAIL_USERNAME = getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = getenv("EMAIL_PASSWORD")
EMAIL_SENDER = getenv("EMAIL_SENDER")
MAINTAINER_EMAIL = getenv("MAINTAINER_EMAIL")
```

**Ein realer Unterschied:** Das Framework macht `load_dotenv(find_dotenv(usecwd=True))`
statt `load_dotenv()` — es sucht die `.env` ab dem **CWD der laufenden App**, nicht neben
`config.py` (das Framework liegt ja in site-packages). Für Cosmopolitan bedeutet das:
Der Prozess muss aus dem Repo-Root starten, sonst wird die `.env` nicht gefunden.
Docker-Compose `working_dir` und `run_pytest.sh` daraufhin prüfen.

---

## 4. Die konkreten Stolperstellen

### 4.1 `logger.py` — drei Divergenzen
- Cosmopolitan filtert zusätzlich `"matplotlib"`, `"PIL"`, `"rasterio"` aus den Logs.
  Die Excluded-Liste muss als Parameter reingereicht werden, nicht hartkodiert bleiben.
- **Tippfehler-Falle:** Cosmopolitan heißt die Funktion `get_logger_config_compuation`
  (fehlendes `t`), das Framework `get_logger_config_computation`. Alle Call-Sites anpassen.
- Docstring-Unterschied, irrelevant.

### 4.2 HTML-IDs — 42 identisch, 12 fehlen
Namen **und** Werte der 42 gemeinsamen Konstanten stimmen exakt überein (inkl.
`ERROR_MODAL_SHARED_ID`, `ERROR_TITLE_DIV_SHARED_ID`, `ERROR_MESSAGE_DIV_SHARED_ID`,
`LOADING_OVERLAY_MODAL_SHARED_ID`, alle `*_LOGS_ID` und `*_JOB_MANAGEMENT_ID`).
Das P1-Gate aus der Boundary-Doc ist für Cosmopolitan damit faktisch erledigt.

Diese 12 Framework-IDs existieren in Cosmopolitan **nicht unter diesem Namen**:

| Framework | Cosmopolitan |
|---|---|
| `WORKER_REFRESH_BTN_WORKER_MANAGEMENT_ID` | `REFRESH_BUTTON_WORKER_MANAGEMENT_ID` |
| `WORKER_KILL_BTN_WORKER_MANAGEMENT_ID` | `KILL_BUTTON_WORKER_MANAGEMENT_ID` |
| `WORKER_CANCEL_BTN_WORKER_MANAGEMENT_ID` | `CANCEL_BUTTON_WORKER_MANAGEMENT_ID` |
| `WORKER_MANAGEMENT_DUMMY_COMPONENT_WORKER_MANAGEMENT_ID` | `DUMMY_DIV_WORKER_MANAGEMENT_ID` |
| `WORKER_STATS_CARD_DIV_WORKER_MANAGEMENT_ID` | `STATS_CARD_DIV_WORKER_MANAGEMENT_ID` |
| `WORKER_LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID` | `LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID` |
| `DOWNLOAD_BUTTON_SHARED_ID` | — (existiert nicht) |
| `RESET_{BODY_DIV,CANCEL_BUTTON,CONFIRM_BUTTON,CONFIRM_MODAL,JOB_STORE}_SHARED_ID` | — (Reset-Feature fehlt in Cosmopolitan) |

Die WORKER-Sechs sind reine Umbenennungen: Sobald die Framework-`worker_management`-Page
übernommen wird, kommen die IDs aus dem Framework und die lokalen Definitionen fallen weg.
Wichtig: die **Werte** ändern sich dabei (`refresh-button-…` → `worker-refresh-btn-…`),
also Playwright-Locators in `test/` mit anpassen.

### 4.3 `error_handling.py` — Struktur identisch, zwei echte Konflikte
Das Framework enthält `_truncate_string`, `_truncate_data`, `handle_error`, das
`error_responds_dict`-Muster und die Basis-Exceptions (`JobNotFound`, `JobExists`,
`InvalidJobID`, `ObjectStorageError`, `WorkerManagement*`) in derselben Form.

Domänenseitig bleiben: `NoMeasurementPointsError`, `MapTileDownloadError`,
`SubmittedException`, `NotSubmittedException`, `NotFinishedException`, das
`USE_ERROR_MESSAGE`-Sentinel und die zugehörigen `error_responds_dict`-Einträge.

Zwei Konflikte:
1. **`FileValidationError` kollidiert.** Das Framework *definiert* eine eigene
   (`cosmo_suite.error_handling.FileValidationError`); Cosmopolitan importiert eine
   gleichnamige aus `soil_moisture_prediction.input_file_parser`. Entscheidung nötig:
   entweder Cosmopolitan fängt beide, oder der Upload-Pfad wrappt die SMP-Exception in
   die Framework-Exception. Nicht stillschweigend überschreiben — sonst greift das
   `except` im Upload-Callback nicht mehr.
2. **`send_mail` ist ein Seiteneffekt im Framework-Handler.** Cosmopolitans
   `handle_error` mailt bei unbehandelten Fehlern an `MAINTAINER_EMAIL`; das Framework
   loggt nur. Das muss als injizierbarer Hook zurückkommen (z.B.
   `handle_error(..., on_unhandled=send_mail_hook)`), sonst gehen die Maintainer-Mails
   verloren. Das Framework hat diesen Hook **noch nicht** — er ist zu ergänzen.
   `error_handling` darf dabei **nicht** `email_service` importieren (Zyklus-Regel).

### 4.4 `background_job_manager.py`
Framework: `BackgroundJobManager` mit `get_job_status`, `get_task_result_info`,
`get_all_tasks_overview`, `revoke_job`, `submit_test_task`, `submit_cleanup_task` und dem
generischen `submit_named_job(...)`. Modul-Level-`__getattr__` liefert
`background_job_manager` als **lazy Singleton** (wird erst beim ersten Zugriff gebaut) —
Cosmopolitan hat dasselbe Muster, also kompatibel.

Domänenseitig bleiben: `NAME_COMPUTATION_TASK`, `NAME_UPDATE_DB_TASK`,
`submit_computation_job(job)`, `submit_update_db_task()` — als dünne Wrapper um
`submit_named_job`. `NAME_CLEANUP_TASK`/`NAME_TEST_TASK` zeigen im Framework auf
`cosmo_suite.tasks.*`; die Celery-Routes müssen entsprechend umgestellt werden, sonst
landen Cleanup/Test-Tasks in keiner Queue.

### 4.5 `layouts.py` — nur teilweise
Framework-`app_layout()` enthält zusätzlich ein Reset-Confirm-Modal samt Callbacks und
importiert dafür `cosmo_suite.job.Job` — Cosmopolitan hat dieses Feature nicht.

Zwei harte Punkte:
- Framework-Navbar linkt auf `dash.get_relative_path("/")`, Cosmopolitan auf
  `dash.page_registry["pages.home"]["relative_path"]`. Der Framework-Weg setzt voraus,
  dass die Domäne eine Page auf `"/"` registriert.
- Framework erwartet `/static/icon_navbar.svg`, Cosmopolitan liefert
  `/static/icon_white.svg`. Das Framework-Wheel enthält **keine** Assets (kein
  `assets/`, kein `static/` im Paket) — Icon-Pfad und Bootstrap-Theme müssen von der
  App kommen. Cosmopolitan lädt Icons lokal und übergibt kein `external_stylesheets`;
  das Framework-Beispiel nutzt CDN (`dbc.themes.FLATLY, dbc.icons.BOOTSTRAP`).
  Prüfen, dass `bi bi-*`-Icons in Framework-Komponenten nicht leer rendern.

### 4.6 `pydantic_models.py`
Das Framework liefert `validate_job_id` (identisches Regex/Längen-Regelwerk, 8–50 Zeichen,
`^\w+$`) und `BaseJobConfig` mit genau zwei Feldern: `job_id` und `upload_file_name`,
plus `model_config = ConfigDict(validate_assignment=True)`.

→ `ModelWebsite` von `BaseJobConfig` erben lassen und das lokale `job_id`-Feld sowie
`validate_job_id` entfernen. Aufpassen: `validate_assignment=True` ist ein
Sicherheitsfeature (kein Modell kann eine ungültige `job_id` bekommen) — nicht abschalten.

### 4.7 `postgres_manager.py` → `db_manager.py`
Deckungsgleich sind: `Base`, `SessionScope` (inkl. `__enter__`/`__exit__`), `_get_session`,
`session_scope`, `query_distinct_modules`, `query_logs`, `delete_logs_older_than`,
`check_existence`, `add_entry`, `update_column`, `set_submitted`, `get_job_columns`,
`delete_job`, `list_jobs` — dieselben 18 Symbole in derselben Reihenfolge.
Ab `_extract_date` (`postgres_manager.py:416`) beginnt reine CRNS/TimeIO-Domäne
(~700 Zeilen, ~25 Methoden) — die bleibt.

Drei Fallstricke:
1. **Klassenname:** Framework `DbManager`, Cosmopolitan `PostgresManager`. Sauberster Weg:
   `class PostgresManager(DbManager):` — dann bleiben alle Call-Sites inkl.
   `PostgresManager.check_existence("test")` im Test-Setup unverändert.
2. **`JobTable`-Spalten:** Framework-`JobTable` hat `job_id, start_date, input_data,
   submitted, notified_end, logs, status, version`. Cosmopolitans ORM hat **zusätzlich
   `prepared_input`**. Die Framework-Version ist damit für Cosmopolitan zu schmal.
   Cosmopolitan definiert seine `JobTable` weiter selbst — aber **auf der
   Framework-`Base`** (`from cosmo_suite.db_manager import Base`), sonst existieren zwei
   Declarative-Registries und `LogTable`/`JobTable` landen in getrennten Metadata-Objekten.
   Dasselbe gilt für `TaskLockTable`, `UpdateTimesCRNS`, `TimeIOInfo`, `CRNSMeasurement`,
   `AppConfig`, `UpdateDbRuns`.
   Randnotiz: Cosmopolitans `docker/init.sql` hat `email` und `celery_task_id` in `jobs`,
   das ORM-Modell aber nicht — diese Abweichung existiert schon heute, nicht durch die
   Integration verursacht. Falls das Absicht ist: Kommentar dazu; falls nicht: Bug.
3. **`LogTable` ist der einzige saubere Lift** — Spalten in beiden Repos identisch.
   Framework-Version verwenden, lokale löschen.

### 4.8 `job.py` — bleibt, Seams injizieren
Gute Nachricht: Cosmopolitans `Job` benutzt bereits **dasselbe Muster** wie das
Framework — `self.model = ModelWebsite(...)`, serialisiert in die Spalte `input_data`,
`_init_from_model`, `_blank_job`, `dump_parameters`, `_get_column_data`, `reload_logs`.
Kein `self.model`-vs-Attribut-Konflikt (das ist Cosmonauts Problem).

Der Framework-`Job` hat drei Klassen-Attribute als Injektionspunkte, die **vor der ersten
Job-Konstruktion** gesetzt sein müssen (Page-Callbacks bauen Jobs, also vor
`app.layout`):

```python
Job.config_model = ModelWebsite          # PFLICHT, sonst RuntimeError (fail-loud)
Job.file_validator = staticmethod(...)   # optional
Job.submit_handler = staticmethod(submit_computation_job)  # PFLICHT für submit()
```

Referenzimplementierung: `examples/csv_profiler/csv_profiler/app.py:29-31` im
Framework-Repo.

Realistische Einschätzung: Cosmopolitans `job.py` hat 802 Zeilen gegenüber 355 im
Framework, davon ist der Löwenanteil CRNS-Logik (`preview_area`, `prepare_input_files`,
`_write_crns`, `safe_input_file`, Projektionen). **Empfehlung: `job.py` in Phase 1
gar nicht anfassen.** Der Framework-`Job` ist noch ein konkreter `Job`, kein `BaseJob`-
Contract — die Vereinheitlichung ist ein eigenes, späteres Stück Arbeit.

---

## 5. Empfohlene Reihenfolge

**Phase 1 — risikofrei, sofort (die drei geschenkten Module):**
1. Pin setzen, `uv lock`, `dotenv`-Kollision klären.
2. `object_storage_manager.py` und `logs_table.py` löschen, Imports umbiegen.
   (0 Diff-Zeilen — reines Suchen/Ersetzen.)
3. `config.py` auf Framework-Basis + Domänen-Extras umstellen; CWD-Annahme der `.env`
   in Docker/Testskripten verifizieren.
4. App starten, durchklicken.

**Phase 2 — kleine Divergenzen:**
5. `logger.py` (Excluded-Liste als Parameter, Typo-Fix an allen Call-Sites).
6. `files_route.py`, `celery_config.py` (`BaseCeleryConfig` subclassen),
   `celery_app.py` (Task-Manifest bleibt lokal, Task-Namen der Framework-Tasks umstellen).
7. `pydantic_models.py`: `ModelWebsite(BaseJobConfig)`.

**Phase 3 — die Substanz:**
8. `postgres_manager.py`: `PostgresManager(DbManager)`, `LogTable` aus dem Framework,
   eigene Tabellen auf die Framework-`Base` umhängen.
9. `error_handling.py`: Basis aus dem Framework, Domänen-Exceptions lokal, `send_mail`
   als Hook (Hook im Framework erst noch bauen).
10. `background_job_manager.py`: Basis nutzen, `submit_*`-Wrapper lokal.
11. Pages `logs`/`job_management`/`worker_management` aus dem Framework; ID-Renames und
    Playwright-Locators nachziehen.
12. `layouts.py`: Navbar/Branding lokal, Rest aus dem Framework.

**Nicht in diesem Durchgang:** `job.py`, `JobTable`-Vereinheitlichung, Plugin-Registry/
`DomainPlugin`-Protocol und die Branding-Layer aus
[`framework-generalization.md`](framework-generalization.md) — davon ist nichts
implementiert; der aktuelle Seam sind schlicht die drei `Job`-Klassenattribute.

---

## 6. Verifikation

Es gibt **keine nennenswerte Framework-Test-Suite** — `cosmo-suite/test/` enthält nur
`test_html_id_enforcement.py`; die echten Tests (db_manager, background_job_manager, e2e)
leben im Beispiel `examples/csv_profiler/test/`. Das Framework ist gegen Cosmopolitan
also **nie gelaufen**. Cosmopolitans eigene Suite ist damit die einzige Absicherung:
nach jeder Phase `./run_pytest.sh`, und die Phase-1-Änderungen zusätzlich manuell
durchklicken (Upload → Submit → Results → Logs → Worker-Management).

Erwartete Bruchstellen in Cosmopolitans `test/conftest.py`: Import des DB-Managers unter
seinem lokalen Namen und der Aufruf `.check_existence("test")` — beides bleibt heil, wenn
`PostgresManager(DbManager)` als Subklasse geführt wird.

Prüfen, dass die Domänen-Grenze hält (das Framework-CI hat dafür ein Grep-Gate in
`.gitlab-ci.yml:41`): nach der Integration darf in `cosmo_suite/` nichts CRNS-spezifisches
auftauchen — falls du Änderungen ins Framework zurückspielst, dort domänenfrei bleiben.
