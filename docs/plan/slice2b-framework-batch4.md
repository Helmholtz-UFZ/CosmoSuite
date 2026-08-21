# Slice 2b: die Persistenz-Naht reparieren, Version 0.6.0

**Repo:** `cosmo-suite` · **Branch:** neu, `slice2b-framework-batch4` off `main` (`f4ca206`)
**Version:** `0.5.0` → **`0.6.0`** · **Erstellt:** 2026-08-21

---

## 0. Warum das kein Nice-to-have ist

`v0.5.0` hat sechs Nahtstellen geliefert. Fünf tragen. Die sechste, die Persistenz,
ist beim ersten Kontakt mit cosmonaut gebrochen, und zwar aus zwei Gründen, die beide
gemessen sind und beide im Framework liegen, nicht in den Apps.

Das ist die Schicht, die das SoftwareX-Paper ausdrücklich als geteilt behauptet:

> "Parameter validation, asynchronous execution, job management, **persistence**,
> deployment, and operational interfaces are reused unchanged."

Und Tabelle 1 führt "Dash to PostgreSQL: Write job records / Read job records" als
Interaktion **des Frameworks** auf. Solange cosmonaut seinen eigenen `db_manager` mit
eigener `Base`, eigener `JobTable` und eigener `LogTable` fährt, ist von den drei
Schichten der Abbildung 2c genau eine nicht geteilt, und es ist die, die in der Tabelle
steht. Dieser Batch ist die Voraussetzung dafür, dass der Satz stimmt.

---

## 1. Befund 1: `JobTable` ist keine Schnittmenge

Die drei `jobs`-DDLs, gemessen am 2026-08-21 aus `docker/init.sql`:

| Spalte | cosmopolitan | cosmonaut | csv_profiler |
|---|---|---|---|
| `job_id`, `start_date`, `submitted`, `notified_end`, `status`, `version` | ja | ja | ja |
| `input_data` | ja | **nein** | ja |
| `logs` | ja | **nein** | ja |
| `email`, `celery_task_id` | ja | ja | nein |
| `prepared_input` | ja | nein | ja |
| `membership_upload`, `predictor_upload`, `stage`, `epsg`, `config` | nein | ja | nein |

Die echte Schnittmenge über alle drei sind **sechs** Spalten. `JobTable` führt acht. Die
zwei zusätzlichen sind genau die, die cosmonaut nicht hat.

Nach der Asymmetrie-Regel in `docs/conventions/database_schema.md` ist eine fehlende
Spalte der Fall, der zur Laufzeit knallt. Die Schnittmenge wurde offensichtlich über
cosmopolitan und csv_profiler geschnitten, und csv_profiler stammt von cosmopolitan ab,
hat also nichts belegt. Cosmonaut wurde nie geprüft.

`email` und `celery_task_id` stehen in zwei von drei DDLs und sind in cosmopolitan tot.
Sie bleiben draußen, das war und ist richtig.

---

## 2. Befund 2: `Base` und `JobTable` im selben Modul schließen jede App aus

Ausgeführt, nicht behauptet:

```python
from cosmo_suite.db_manager import Base
class AppJobTable(Base):
    __tablename__ = "jobs"
    ...
# InvalidRequestError: Table 'jobs' is already defined for this MetaData instance.
```

Wer die Registry importiert, registriert die Tabelle mit. Beide Apps haben eine eigene
`jobs`-Tabelle mit eigenen Spalten. Keine von beiden kann sie auf der Framework-`Base`
deklarieren, solange das Framework dort selbst eine konkrete `jobs` hinstellt. Der
Zwei-Engine-Zustand ist damit nicht Bequemlichkeit der Apps, sondern vom Framework
erzwungen.

---

## 3. Die Entscheidung: Mixin plus konfigurierbare Tabelle

Das Framework liefert die **Spalten** und die **Maschinerie**, jede App deklariert ihre
**eigene konkrete Klasse**. Deklarative Mixins sind dafür das dokumentierte
SQLAlchemy-Mittel: `Column`-Objekte auf einer nicht gemappten Mixin-Klasse werden pro
gemappter Subklasse kopiert. Für sechs skalare Spalten braucht es kein `declared_attr`.

Was ausdrücklich verworfen wurde, damit es nicht wieder aufkommt:

| Alternative | Warum nicht |
|---|---|
| Single-Table-Inheritance | braucht einen Discriminator und teilt **eine** Tabelle. Die Apps haben physisch verschiedene Tabellen, und es läuft ohnehin nur eine App pro Prozess. |
| `AbstractConcreteBase` | existiert für polymorphe Abfragen über Geschwistertabellen. Es wird nie über Apps hinweg abgefragt. |
| Zwei `Base` behalten | der Status quo, den `database_schema.md` selbst als "keine Stilfrage" führt: zwei Registries, zwei Engines, zwei Pools gegen dieselbe Datenbank. |
| `input_data` und `logs` in cosmonauts DDL nachziehen | erzeugt genau den toten Ballast, den dieselbe Konvention kritisiert. Cosmonaut nutzt Framework-`Job` nicht, es hat `CosmonautJob` über `BaseJob`. |

Die Naht ist dieselbe Form wie `serve_files(app, job_class=...)` und
`layouts.default_wrapper_class`, also kein neues Idiom.

---

## 4. Die Änderungen, in dieser Reihenfolge

### 4.1 `JobColumns` als Mixin, konkrete `JobTable` entfernen

In `cosmo_suite/db_manager.py`:

```python
class JobColumns:
    """Die sechs Spalten, die jede App-`jobs`-Tabelle gemessen führt.

    Kein Mapping und keine Tabelle: jede App deklariert ihre eigene konkrete
    Klasse hieraus, siehe docs/conventions/database_schema.md.
    """

    job_id = Column(String, primary_key=True)
    start_date = Column(Date)
    submitted = Column(Boolean)
    notified_end = Column(Boolean)
    status = Column(String)
    version = Column(String)
```

Die konkrete `class JobTable(Base)` fällt **ganz weg**. Der Name `JobTable` bleibt für
die konkreten Klassen der Apps frei, dort ändert sich also kein Name.

Umbenennung mit Absicht: `JobColumns` statt `JobTable` erzwingt, dass jede der 14
Aufrufstellen einmal angefasst und geprüft wird, statt stillschweigend weiterzulaufen.

### 4.2 `DbManager.job_table` als Naht

`DbManager` hält die Klasse, die die App gesetzt hat:

```python
class DbManager:
    # Von der App gesetzt, per Modul-Zuweisung auf DbManager selbst.
    job_table = None

    @classmethod
    def _job_table(cls):
        if cls.job_table is None:
            raise JobTableNotConfigured()
        return cls.job_table
```

Die zwölf `JobTable`-Referenzen in `check_existence`, `add_entry`, `update_column`,
`update_submitted`, `get_job_columns`, `delete_job`, `list_jobs` gehen über
`cls._job_table()`.

**Die Falle, und sie muss in den Docstring:** die Zuweisung gehört auf `DbManager`
selbst, nicht auf eine Subklasse. Framework-Seiten rufen `DbManager.list_jobs()`
direkt, dort ist `cls` die Basisklasse. Wer `PostgresManager.job_table = JobTable`
setzt, hat es für die eigenen Aufrufe konfiguriert und für die Framework-Seiten nicht.
Das ist derselbe Fehlermodus wie die drei in `framework_page_imports.md`.

`JobTableNotConfigured` kommt neu in die Exception-Hierarchie. Ein benannter Fehler mit
Hinweis auf die Konvention, statt `AttributeError: 'NoneType' object has no attribute`.
Das ist Vertragsdurchsetzung an einer Stelle, keine defensive Programmierung.

### 4.3 `list_jobs` verliert die hartcodierten Spalten

`list_jobs` ist die **einzige** Methode, die `input_data` und `logs` namentlich nennt
(Zeilen 340 und 344). Alle anderen brauchen nur `job_id` und `submitted`, liegen also in
den sechs. `get_job_columns` baut sein Dict schon generisch aus
`__table__.columns`. `list_jobs` macht es genauso:

```python
job_info[job_row.job_id] = {
    column.name: getattr(job_row, column.name)
    for column in cls._job_table().__table__.columns
}
```

**Zu prüfen:** die Job-Management-Seite konsumiert das Dict. Zusätzliche Schlüssel sind
für sie harmlos, fehlende nicht. Nach der Änderung liefert sie pro App mehr Spalten als
vorher, nie weniger. Einmal die Seite öffnen und die Tabelle ansehen.

### 4.4 `Job` greift über den Manager, nicht per Import

`cosmo_suite/job.py:28` importiert `JobTable`, `job.py:314` nutzt
`JobTable.__table__.columns.keys()`. Beides über `DbManager` führen. Danach hat
`cosmo_suite/job.py` **keinen** Bezug mehr auf eine konkrete Tabelle.

### 4.5 csv_profiler deklariert seine eigene `JobTable`

csv_profiler hat heute **null** Referenzen auf `JobTable`, es lebt vollständig von
Framework-`Job` und `DbManager`. Nach 4.1 muss es die Klasse selbst hinstellen:

```python
class JobTable(JobColumns, Base):
    __tablename__ = "jobs"

    input_data = Column(JSON)
    logs = Column(String)

DbManager.job_table = JobTable
```

Das ist der Punkt, an dem die Referenzdomäne aufhört, ein Sonderfall zu sein: sie
demonstriert die Naht, die die beiden Apps benutzen werden, statt sie zu umgehen. Für
das Paper ist genau das der Beleg.

`prepared_input` steht in csv_profilers DDL und wird von seinem Code nicht gebraucht.
Nicht mitmappen, nicht aufräumen.

### 4.6 `track_task_name` Default drehen

Gemessen: **beide** Apps rufen ausschließlich `submit_named_job`, und das verdrahtet
`track_task_name=True` fest. `submit_job` soll genau diese Methode ersetzen, hat aber
`False` als Default. Damit ist jede Migration auf die neue Naht eine stille Regression
auf der Worker-Management-Seite, wo ein widerrufener Task dann als "Unknown" erscheint.

Default auf `True`. Die Begründung im aktuellen Docstring ("kostet einen Backend-Write
pro Submission") wiegt ein Redis-`SET` pro Job gegen eine kaputte Seite auf. Wer den
Write wirklich sparen will, schreibt `False` hin.

Ein explizites `track_task_name=True` in einer App bleibt danach korrekt und lesbar.

### 4.7 Dokumentation nachziehen

- `docs/conventions/database_schema.md`: die Schnittmenge auf sechs Spalten korrigieren,
  die Tabelle aus §1 dieses Plans übernehmen, den Abschnitt "Warum eine zweite `Base`
  keine Stilfrage ist" auf den neuen Stand bringen (das Framework stellt keine konkrete
  `jobs` mehr hin, deshalb ist eine `Base` jetzt überhaupt erreichbar), und die
  Zuweisungsfalle aus 4.2 aufnehmen.
- Der Satz "gemessen über beide Apps und die Referenzdomäne" war falsch. Er wird
  ersetzt, nicht nur die Zahl.

---

## 5. Die Abnahme, die zählt

Ein Test, der beweist, dass das Framework keine `jobs`-Tabelle mehr registriert:

```python
def test_framework_registers_no_jobs_table():
    """Sonst kann keine App ihre eigene jobs-Tabelle deklarieren."""
    import cosmo_suite.db_manager, cosmo_suite.job, cosmo_suite.files_route
    from cosmo_suite.db_manager import Base
    assert "jobs" not in Base.metadata.tables
    assert "logs" in Base.metadata.tables
```

Das ist die eine Zeile, die den ganzen Batch trägt. Sie muss **nach** dem Import jedes
Framework-Moduls gelten, das eine App anfassen könnte, `files_route` eingeschlossen, denn
dessen Default `job_class=Job` zieht `cosmo_suite.job` mit herein.

Dazu ein Test, der `JobTableNotConfigured` auslöst, indem er `DbManager.list_jobs()`
ohne Zuweisung ruft.

---

## 6. Ausdrücklich NICHT in diesem Batch

- Kein `Alembic`, keine Migrationen. Die DDL bleibt in den `init.sql` der Apps.
- Kein Anfassen von `LogTable`. Die ist in allen drei Codebasen identisch, gehört dem
  Framework und bleibt konkret.
- Keine Vereinheitlichung der `jobs`-Schemata der Apps. Die Spalten bleiben, wo sie
  sind, das ist der Sinn der Naht.
- Kein `email`/`celery_task_id` in die Schnittmenge.

---

## 7. Definition of Done

- [ ] `Base.metadata.tables` enthält nach Import aller Framework-Module kein `jobs`.
- [ ] `JobColumns` führt exakt sechs Spalten.
- [ ] Keine `JobTable`-Referenz mehr in `cosmo_suite/`, weder Import noch Nutzung.
- [ ] `list_jobs` nennt keine Spalte namentlich.
- [ ] `submit_job` hat `track_task_name=True` als Default, Docstring passend.
- [ ] csv_profiler deklariert seine `JobTable` und weist sie auf `DbManager` zu, die
      Suite ist grün, Job-Management-Seite und Log-Seite rendern echte Daten.
- [ ] `database_schema.md` korrigiert, inklusive der Zuweisungsfalle.
- [ ] `version = 0.6.0` in `pyproject.toml`, Tag `v0.6.0` nach dem Merge.

---

## 8. Konventionen

`docs/conventions/database_schema.md`, `framework_page_imports.md`,
`error_handling.md` (für `JobTableNotConfigured`), `testing.md`.

Und die Regel, die für diesen Batch besonders gilt: eine Schnittmenge wird über **alle**
Konsumenten gemessen, nicht über die, die voneinander abstammen.
