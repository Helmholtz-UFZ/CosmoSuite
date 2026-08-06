# Slice 1b — Framework-Batch 2 → `v0.4.0`

**Repo:** `cosmo-suite` · **Branch:** neu, `slice1b-framework-batch2` off `main`
**Vorgänger:** `v0.3.0` (beide Apps laufen darauf) · **Erstellt:** 2026-08-06

---

## 0. Warum dieser Batch

Slice 1 ist durch: beide Apps importieren `cosmo_suite@v0.3.0`, beide Suites grün.
Dabei hat COSMONAUT — der **zweite** Consumer, und damit der erste echte Test des
Frameworks — sechs Stellen gefunden, an denen die Framework-Version eine **Regression**
gewesen wäre. Er hat sie lokal umgangen. Genau das darf nicht stehenbleiben: umgeht ein
Consumer sie lokal, trifft sie den dritten wieder.

Dieser Batch zieht die Umgehungen ins Framework hoch. Er ist damit inhaltlich das, was
das Paper behauptet — ein Framework, das die Bedürfnisse mehrerer Anwendungen aufnimmt.

**Parallelität:** COSMOPOLITAN arbeitet währenddessen an seinem Slice 1b **gegen den
eingefrorenen `v0.3.0`**. Keine Abhängigkeit in diese Richtung. COSMONAUTs Slice 1b
hängt dagegen vollständig an diesem Batch und startet erst nach `v0.4.0`.

Belegquelle für alle Punkte: `../ufz-cosmonaut/docs/project-state.md`, Eintrag
2026-08-06, Zeilen 20–29.

---

## 1. `BaseCeleryConfig` — Zeitlimits raus aus dem Default

`cosmo_suite/celery_config.py:85-86`:
```python
task_soft_time_limit = 3600   # 1 hour soft limit
task_time_limit = 3900        # 65 minutes hard limit
```

COSMONAUT hat beide auf `None` überschrieben. Begründung, gemessen: Sensor-Routing ist
O(n²) und nicht kachelbar — der 65-Minuten-Hard-Kill trifft **genau die großen Surveys,
für die die App existiert**. COSMONAUT hatte vorher kein Limit; das Framework hat also
ein Verhalten eingeführt, das der Consumer nie wollte.

**Änderung:** beide Defaults auf `None`. Ein Framework darf keine Laufzeitobergrenze
erzwingen, deren richtigen Wert nur die Domäne kennt.

**Vor dem Merge abstimmen:** COSMOPOLITAN erbt `BaseCeleryConfig` und hat die Limits
bisher stillschweigend geerbt. Wenn dort ein Limit gewollt ist, setzt es COSMOPOLITAN
künftig **explizit** in seiner `CeleryConfig` — das ist der Punkt der Änderung. Kurz beim
cosmopolitan-Agenten rückfragen, damit nicht unbemerkt ein Schutz wegfällt.

---

## 2. `BaseJobConfig` aufspalten

`cosmo_suite/pydantic_models.py`: `BaseJobConfig` bringt neben `job_id` auch
`upload_file_name` mit. COSMONAUTs `JobTable` hat dafür keine Spalte, `CosmonautJob.save()`
bricht (gemessen). Der Consumer musste deshalb nur `validate_job_id` importieren und den
Rest von Hand nachbauen.

Das ist ein Contract-Fehler: `upload_file_name` gehört zum Nutzungsmuster des
Framework-`Job` („persist, reload, and track the single uploaded input file"), nicht zum
Minimalvertrag einer Job-Konfiguration.

**Änderung — aufspalten:**

```python
class BaseJobConfig(BaseModel):
    """Minimal contract: a valid job_id and assignment validation."""
    job_id: Annotated[str, Field(...), AfterValidator(validate_job_id)]
    model_config = ConfigDict(validate_assignment=True)


class UploadJobConfig(BaseJobConfig):
    """Adds the single-upload-file tracking the framework Job expects."""
    upload_file_name: Optional[str] = Field(None, ...)
```

`examples/csv_profiler/csv_profiler/pydantic_models.py` auf `UploadJobConfig` umstellen.
`cosmo_suite/job.py` dokumentiert dann, dass es `UploadJobConfig` erwartet.

Danach können **beide** Apps von `BaseJobConfig` erben, ohne eine Spalte erfinden zu
müssen. `validate_assignment=True` kommt dabei mit — in COSMONAUT fehlte das bisher
komplett (`job.model.job_id = "short"` umging die Validierung).

> ⚠️ **COSMOPOLITAN ist betroffen und muss mitziehen.**
> `cosmopolitan_app/pydantic_models.py:32` ist `class ModelWebsite(InputParameters,
> BaseJobConfig)`, und der Docstring darunter benennt ausdrücklich, dass `BaseJobConfig`
> „the generic `upload_file_name` field" beisteuert. Nach der Aufspaltung muss
> `ModelWebsite` auf **`UploadJobConfig`** wechseln, sonst verliert es das Feld.
> Diese Änderung **nicht ohne Abstimmung mit dem cosmopolitan-Agenten mergen.**

---

## 3. `object_storage_manager` — drei Parameter

Der größte Einzelposten. COSMONAUT hält deshalb noch 315 Zeilen lokal.

**3.1 `get_files` überschreibt bedingungslos.** COSMONAUTs Version fährt
`--ignore-existing` (Commit `ff62119`) — das ist **tragend**: ohne den Schalter
überschreibt eine veraltete Remote-Kopie ungesyncte Street-Edits. Die Framework-Version
würde diese Zeile still rückgängig machen.

```python
def get_files(..., overwrite: bool = False) -> ...:
```
**Default `False`** (also `--ignore-existing`). Der datenverlustfreie Weg ist der
Default; wer überschreiben will, sagt es.

> ⚠️ **Das ändert COSMOPOLITANs Verhalten still.** Diese App hat ihren lokalen
> `object_storage_manager` in Slice 1 **komplett gelöscht** und ruft die
> Framework-Funktion direkt: `cosmopolitan_app/job.py:249` → `get_files(self.job_id)`
> (dazu `save_files` in `:646`). Heute überschreibt dieser Aufruf bedingungslos; nach dem
> Default-Flip nicht mehr. Ob das dort ein Fix oder eine Regression ist, weiß nur die
> Domäne — der Aufruf lädt Job-Dateien zum Arbeiten herunter, und `--ignore-existing`
> könnte veraltete lokale Kopien stehen lassen.
> **Vor dem Merge klären:** entweder COSMOPOLITAN setzt an `job.py:249` explizit
> `overwrite=True`, oder es bestätigt, dass der neue Default dort richtig ist.
> Nicht stillschweigend umstellen.

**3.2 Subprozess-Timeouts.** `run_rclone_with_retry` hat keinen `timeout` — ein hängender
rclone blockiert den Worker unbegrenzt. Timeout als Parameter mit sinnvollem Default.

**3.3 `check_connection`-Precheck.** COSMONAUT prüft die Erreichbarkeit des Remotes,
bevor es einen Transfer startet; sonst läuft die Retry-Schleife gegen eine tote Adresse.

Alle drei so schneiden, dass COSMONAUT seinen lokalen Wrapper **ersatzlos löschen** kann
— das ist das Abnahmekriterium, nicht „Parameter existiert".

---

## 4. `logger` — `excluded_packages` als Parameter

Beide Apps filtern zusätzliche Pakete aus den Logs (COSMOPOLITAN: `matplotlib`, `PIL`,
`rasterio`). Beide halten dafür einen Shim lokal — COSMONAUT 162 Zeilen.

`ExcludeSubmodulesFilter` bzw. die `get_logger_config_*`-Funktionen bekommen einen
`excluded_packages`-Parameter. Abnahmekriterium: der Shim in beiden Apps verschwindet.

---

## 5. `WEB_WORK_DIR` — `abspath` auflösen

`cosmo_suite/config.py:51` liest `WEB_WORK_DIR` roh. COSMONAUT muss es lokal
`os.path.abspath`-auflösen, **sonst 404t `send_from_directory` jedes Job-Bild**: Flask
löst relative Pfade gegen `app.root_path` auf (= das App-Paket), nicht gegen das CWD.

Das ist eine stille Falle wie `ObjectStorageError` — kein Importfehler, kein
Testfehlschlag, nur kaputte Bilder zur Laufzeit.

```python
WEB_WORK_DIR = os.path.abspath(getenv("WEB_WORK_DIR"))
```
`JOB_WORK_DIR_TEMPLATE` erbt das automatisch. Prüfen, dass `examples/csv_profiler`
dadurch nicht bricht.

---

## 6. `layouts` — Reset-Feature hinter Opt-in, Wrapper für Page-Container

**6.1 Zwei Callbacks feuern nie.** `open_reset_modal` (`layouts.py:233`) und
`handle_reset_confirm` (`:250`) gehören zu einem Reset-Feature, das **keine** der beiden
Apps hat. COSMONAUT hat verifiziert, dass sie **keine** „nonexistent object"-Fehler
erzeugen (0 Console-Messages, 0 Devtools-Cards) — sie feuern schlicht nie. Also kein
Bug, aber toter Code im Prozess jedes Consumers.

Hinter ein Opt-in legen (z.B. `app_layout(with_reset=False)`), damit ein Consumer nicht
Callbacks für ein Feature registriert, das er nicht anbietet. `toggle_navbar_collapse`
(`:147`) bleibt — der wird gebraucht.

**6.2 `page_container_column_layout` hat keinen Wrapper.** COSMONAUT musste
`style.css` umschreiben, weil die Funktion keine Möglichkeit bietet, eine Marker-Klasse
(dort `.no-map-page`) auf einen umschließenden Container zu legen — beide adoptierten
Seiten rendern sonst gequetscht neben der Karte, mit abgeschnittenen Grid-Headern.

Einen optionalen `wrapper_class`-Parameter ergänzen. Danach kann COSMONAUT die
CSS-Umgehung zurücknehmen.

---

## 7. README — die zwei Consumer-Stolpersteine dokumentieren

Beide Apps sind über dieselben zwei Dinge gestolpert, die in **keinem** Plan standen:

1. **`[tool.hatch.metadata] allow-direct-references = true`** ist Pflicht, sonst weist
   hatchling den `git+https://`-Pin zurück.
2. **`git` muss im CI-Image installiert sein.** `uv export` gibt die Dependency als
   `git+https://`-URL aus; ohne `git` bricht der Image-Build bei der nächsten
   `uv.lock`-Änderung. COSMONAUT hat es in `docker/ci.Dockerfile` nachgezogen.

Beides in einen Abschnitt „Consuming this framework" ins `README.md`. Das trifft jeden
künftigen Consumer und ist die billigste Zeile Dokumentation im ganzen Projekt.

---

## 8. Ausdrücklich NICHT in diesem Batch

- **`on_unhandled`-Hook für `handle_error`.** Gehört zu Slice 2 (`error_handling`), nicht
  hierher. Solange er fehlt, bleibt `error_handling` in beiden Apps lokal.
- **`files_route`: generische Download-Route.** Dem Framework fehlt ein Gegenstück zu
  COSMONAUTs `/download/<job_id>/route.gpx` (QR-/Mail-Ziel). Beide Apps halten
  `files_route` deshalb lokal (84 bzw. 131 Z.). Ein registrierbarer Domänen-Dateipfad
  wäre die saubere Lösung — aber das ist Entwurfsarbeit, kein Parameter. Slice 2.
- **`db_manager`-Vereinheitlichung.** Der Kern von Slice 2, siehe §9.

---

## 9. Was dieser Batch bewusst offen lässt (für Slice 2 protokollieren)

Nach Slice 1 laufen in **beiden** Apps zwei SQLAlchemy-Engines im selben Prozess: die der
App und die des Frameworks (`cosmo_suite/db_manager.py:98` vs. das lokale Pendant), mit
zwei getrennten `Base`-Registries, die beide `LogTable`→`logs` und `JobTable`→`jobs`
mappen. In COSMONAUT ist das seit Slice 1 real, in COSMOPOLITAN ab dessen Slice 1b.

Es funktioniert — der Framework-`DbManager` wird nur für Log-Queries verwendet, das
Schema passt, verifiziert an laufenden Apps. Aber es sind zwei Connection-Pools gegen
dieselbe Datenbank und zwei Mapper für dieselben Tabellen.

**Slice 2 löst das**, indem die Apps ihre Tabellen auf die Framework-`Base` umhängen.
Hier nur festhalten, nicht anfassen.

---

## 10. Verifikation und Tag

```bash
cd examples/csv_profiler && ./run_pytest.sh          # einziger echter Prüfstand
cd /home/trinkle/git/cosmo-suite
uv run ruff format --check cosmo_suite test && uv run ruff check cosmo_suite test
grep -rnE --include='*.py' 'csv_profiler|ProfileConfig|computation_module|validate_csv|profile_csv|CSV_UPLOAD' cosmo_suite/   # leer
```

Fertig heißt: Beispielsuite grün, `ruff` sauber, `domain-free`-Gate leer,
`version = "0.4.0"` in `pyproject.toml`, `git tag v0.4.0 && git push --tags`.

**Danach — und erst danach — startet COSMONAUTs Slice 1b.** COSMOPOLITAN re-pinnt auf
`v0.4.0`, sobald sein eigenes Slice 1b durch ist.

---

## 11. Konventionen

`CLAUDE.md` gilt: keine `dict.get()`, kein bare `except Exception`, keine Inline-Imports,
HTML-IDs nur aus `cosmo_suite/constants/html_ids.py`, kein Inline-CSS. Abweichung mit
begründendem Kommentar.
