# Database Schema, `Base`, and Who Owns the DDL

## One `Base` per process

`cosmo_suite.db_manager.Base` is the framework's declarative registry and a
**documented export point**. Every table in a Cosmo Suite process belongs on it:

```python
from cosmo_suite.db_manager import Base

class RouteTable(Base):
    __tablename__ = "routes"
    ...
```

`DbManager` owns the engine and the session factory. An app uses
`DbManager.session_scope()` for its own queries rather than creating a second
engine.

### Why a second `Base` is not a style question

Declaring a second `DeclarativeBase` in the same process creates a second mapper
registry, and in practice a second engine and a second connection pool against
the same database. Both apps run exactly that today: their own `Base` beside the
framework's, each mapping `logs` to `logs` and `jobs` to `jobs`. It works only
because the framework's `DbManager` is confined to the log queries the framework
pages issue — nothing arbitrates between the two mappers, and nothing would
notice if they drifted apart.

Unwinding that is app-side work; the framework's part is to make the shared
`Base` an explicit thing to import rather than an internal detail.

---

## `JobTable` is an ORM mirror, not the schema

The authoritative DDL for the `jobs` table lives in **each app's own
`init.sql`**. `cosmo_suite.db_manager.JobTable` maps the strict intersection of
what every app is known to have, so framework code can read and write a job row
without knowing which app it is running in.

The intersection, measured across both apps and the reference domain on
2026-08-19 and frozen for the duration of Slice 2:

```
job_id, start_date, input_data, submitted, notified_end, logs, status, version
```

What stays app-side:

| Column | Where | Why it is not in the intersection |
| --- | --- | --- |
| `prepared_input` | COSMOPOLITAN | app-specific stage tracking |
| `email` | COSMOPOLITAN `init.sql` | in the DDL only; never read or written, no ORM mapping |
| `celery_task_id` | COSMOPOLITAN `init.sql` | in the DDL only; the app's `celery_task_id` is an in-memory attribute with no ORM mapping, and there is no raw SQL against `jobs` |

`email` and `celery_task_id` are dead schema ballast: they exist in one app's
table and in no code path. They are irrelevant to the intersection and were
deliberately ignored when it was cut.

### The asymmetry that makes this safe

An **extra** column in the physical table is harmless to this mapper — SQLAlchemy
simply does not map it. A **missing** column is not: the first query against it
fails at runtime. Cutting the intersection rather than the union is what makes
one ORM class safe against several physical schemas.

### Changing it

Adding a column to `JobTable` is a framework-wide schema commitment. Every
consuming app's `init.sql` has to grow the column *first*, in a release that
ships before the framework tag that maps it. The reverse order breaks whichever
app deploys last.

App-specific columns never go here. An app that needs one adds it to its own
`init.sql` and maps it on a subclass or a separate table, on the framework
`Base`.

---

## `LogTable`

`LogTable` is the one table that lifted cleanly: identical in all three code
bases, owned by the framework, written by `logger.PostgreSQLHandler` and read by
the logs page. It is not an intersection — it is the schema.
