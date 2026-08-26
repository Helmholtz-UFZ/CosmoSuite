# Slice 3: die vier Lücken schließen, die beide Apps unabhängig gefunden haben, Version 0.7.0

**Repo:** `cosmo-suite` · **Branch:** neu, `slice3-framework-batch5` off `main` (`d20ee6c`, `v0.6.2`)
**Version:** `0.6.2` → **`0.7.0`** · **Erstellt:** 2026-08-26

---

## 0. Warum dieser Batch anders begründet ist als die vorherigen

Slice 2 lief in beiden Apps parallel, von zwei Agenten, die nichts voneinander wussten.
Beide sind an **denselben zwei** Framework-Grenzen stehengeblieben, und beide haben sich
verschieden herausgewunden. Das ist der stärkste Beleg, den es für einen
Framework-Bedarf gibt: nicht ein App-Sonderwunsch, sondern zwei unabhängige Messungen
derselben Lücke.

Gemessen am 2026-08-26 auf `origin/main` beider Apps, nach dem Merge:

| Modul | cosmopolitan | cosmonaut |
|---|---|---|
| `error_handling.py` | **274 Z.**, eigenes `handle_error` | 108 Z., mutiert dafür `error_responds_dict` des Frameworks im Prozess |
| `create_header` | lokal, 190 ff. | gelöscht, Framework-Fassung übernommen |

Nach diesem Batch ist `error_handling` in cosmopolitan löschbar und cosmonaut hört auf,
in ein Framework-Modul hineinzuschreiben.

---

## 1. `handle_error` bekommt die Antworttabelle und die erwarteten Fehler herein

### Befund

Das Framework hält **drei** Ausnahmen für erwartet, cosmopolitan **sechs**:
`NotFound`, `NotFinishedException`, `JobNotFound`, `InvalidJobID`, `SubmittedException`,
`MapTileDownloadError`. Die drei zusätzlichen sind normale Nutzerzustände. Mit der
Framework-Fassung würde jeder davon bei jedem Auftreten den Maintainer anmailen.

Dazu zwei Dinge, die die Framework-Fassung nicht hat:

- **Der Sentinel.** `USE_ERROR_MESSAGE = "use_error_message"` als Nachricht in der
  Tabelle heißt "zeig dem Nutzer `str(error)`". Ohne ihn gibt es keinen Weg, eine
  Parser-Meldung durchzureichen.
- **Ein brauchbarer `FileValidationError`-Eintrag.** Und hier liegt der Punkt, der die
  Sache entscheidet: cosmopolitans `FileValidationError` kommt aus
  `soil_moisture_prediction.input_file_parser`, also **aus dem Rechenmodul**. Das ist eine
  andere Klasse als `cosmo_suite.error_handling.FileValidationError`, nicht dieselbe mit
  anderem Verhalten. Kein Framework-Eintrag kann sie jemals treffen. Eine App **muss**
  eigene Einträge registrieren können.

Cosmonauts Ausweg zeigt dasselbe von der anderen Seite: es ruft
`error_responds_dict.update(...)` auf dem **Framework-Modul** auf, weil das
Framework-`handle_error` genau dieses Modul-Dict liest. Das funktioniert heute und ist
still kaputt, sobald das Framework das Dict irgendwo kopiert oder die Importreihenfolge
sich ändert. Es ist ein Workaround für eine fehlende Naht, kein Muster.

### Änderung

```python
def handle_error(
    error,
    *,
    on_unhandled: Callable[[Exception], None] | None = None,
    error_responses: dict | None = None,
    expected_errors: tuple[type[Exception], ...] | None = None,
) -> None:
```

- `error_responses` wird **über** die Framework-Tabelle gelegt, nicht statt ihr. Die App
  liefert nur ihre eigenen Einträge und Überschreibungen.
- `expected_errors` **ersetzt** die Framework-Menge, wenn gesetzt. Nicht ergänzen: eine
  App muss auch einen Eintrag herausnehmen können.
- Der Sentinel wandert ins Framework und wird exportiert. Er gehört zur Tabelle, nicht
  zur App.
- Das Modul-Dict `error_responds_dict` bleibt als Default und Exportpunkt. Es darf danach
  **niemand mehr von außen mutieren**, das gehört in den Docstring.

Beide Apps wiren `handle_error` schon über `functools.partial` in `app.py`. Die neuen
Argumente passen also in die bestehende Naht, ohne dass eine Aufrufstelle die Form
ändert.

**Zu prüfen:** dass `expected_errors=None` genau das heutige Verhalten liefert. Das ist
die Bedingung dafür, dass cosmonaut beim Re-Pin nichts merkt.

---

## 2. `create_header` bekommt ein optionales `id`

### Befund

Die Framework-Fassung (`layouts.py:182`) stempelt **keine** ID. Cosmopolitans Fassung
(`layouts.py:190`) stempelt drei: `id`, `{id}-title`, `{id}-subtitle`. Drei
Hydration-Callbacks zielen auf `{id}-subtitle`, und bei
`suppress_callback_exceptions=True` hätten sie nach einer Übernahme lautlos ins Leere
gezielt.

Cosmonaut hatte dieselbe lokale Fassung und hat sie gelöscht, weil ihr Default `id=""`
bei jedem Aufruf ohne ID die kollidierenden `""`, `"-title"`, `"-subtitle"` erzeugte.

Beide Befunde zeigen auf dieselbe Signatur:

```python
def create_header(title, subtitle, bg_color="bg-info", id=None, rounded=True):
```

IDs werden nur gestempelt, wenn `id` gesetzt ist. `id=None` ist die
Framework-Fassung von heute, `id="job-header"` die von cosmopolitan. Der Default `""`
kommt **nicht** zurück, das war der Bug.

Die `# nocheck`-Kommentare wandern mit, die IDs sind dynamisch konstruiert.

**Kein Verhaltensunterschied, nicht erhalten:** die lokale Fassung setzt bei leerem
Subtitle ein `None` in `children`, die Framework-Fassung lässt das Element weg. Dash
rendert beides gleich. Die Framework-Variante gewinnt.

---

## 3. Der Callback auf Modulebene in `layouts`

### Befund, und er ist anders als vermutet

`cosmo_suite/layouts.py:161` registriert `toggle_navbar_collapse` beim **Import**. Was
das heute tatsächlich bewirkt, gemessen an den ID-Strings:

| App | ID | Wirkung |
|---|---|---|
| cosmopolitan | `navbar-collapse-div-shared-id`, **identisch** mit der Framework-ID, in der eigenen Navbar gemountet (`layouts.py:181`) | der Navbar-Toggle funktioniert **nur** als Nebenwirkung des Imports. Eigener Callback existiert nicht. |
| cosmonaut | `navbar-collapse-nav-shared-id`, eigener Callback in `layout.py:797` | der Framework-Callback ist registriert und **tot**: er zielt auf eine ID, die nie gemountet wird. |

Es ist also kein Duplicate-Callback und kein Absturz. Es ist eine unsichtbare Kopplung
auf der einen Seite und eine Totregistrierung auf der anderen, beide still. Wenn
cosmopolitan je aufhört, `cosmo_suite.layouts` zu importieren, stirbt sein Navbar-Toggle
ohne eine einzige Meldung.

### Änderung

Der Callback wandert in `register_navbar_callbacks()`. Kein `@callback` mehr auf
Modulebene.

**Und `app_layout()` ruft die Funktion mit.** Der Defekt war nie "das Framework
registriert einen Callback", sondern "ein *Import* registriert einen Callback". Eine
Funktion, die die Navbar mountet und dabei den Callback für genau diese Navbar
registriert, ist Ko-Lokation, keine versteckte Nebenwirkung. Der Unterschied zu
`with_reset` ist messbar: `with_reset` ist optional, dort wäre eine ungefragte
Registrierung ein Feature im Prozess des Konsumenten. `app_layout()` mountet die Navbar
unbedingt — es gibt keinen Aufruf, in dem der Callback nicht gebraucht wird.

`register_navbar_callbacks()` bleibt öffentlich und idempotent, denn cosmopolitan
mountet die Framework-ID in seiner eigenen Navbar und ruft `app_layout()` nicht. Genau
dafür ist die Funktion da; **für cosmopolitan heißt das eine Zeile Nacharbeit.** Der
AST-Test bleibt unberührt, er verbietet nur die Modulebene.

---

## 4. Die Testlücke, die zwei Wochen Produktionsausfall gekostet hat

`docker/worker.Dockerfile` in cosmonaut importierte im `CMD` ein Modul, das Slice 1b
gelöscht hatte. Der Import steht als String in einem Dockerfile: kein Linter liest ihn,
und die Suite startet den Worker über `uv run celery`, nie über den Image-CMD. Weil der
Befehl mit `;` verkettet war, startete Celery trotz `ModuleNotFoundError` weiter, nur
ohne konfiguriertes rclone-Remote. Das UI meldete "Road network construction failed",
drei Schichten von der Ursache entfernt. Behoben in cosmonaut, das `&&` ist dabei der
eigentliche Fix.

Die Fehlerklasse ist nicht cosmonaut-spezifisch: **alle drei** Konsumenten bauen ein
Worker-Image mit einem `setup_remote()`-Aufruf im `CMD`. Deshalb gehört der Test ins
Framework-Muster.

Ein CI-Schritt, der das gebaute Worker-Image hochfährt und nur den Storage-Setup-Teil
ausführt:

```yaml
worker-image-smoke:
  stage: test
  script:
    - docker build -f docker/worker.Dockerfile -t worker-smoke .
    - docker run --rm worker-smoke python3 -c
        "from cosmo_suite.object_storage_manager import setup_remote; setup_remote()"
```

**Korrektur bei der Umsetzung: der Job gehört in die Apps, nicht hierher.** `cosmo-suite`
baut in CI kein einziges Image und hat keine Runner-Tags; der Job würde
docker-in-docker-Infrastruktur allein für sich brauchen. Die Apps bauen ihr Worker-Image
längst und laufen auf einem Runner, der das kann. Das Argument, das den Punkt
entscheidet: csv_profilers Worker-Image wird nirgends deployt. Der Ausfall lief in
cosmonauts **Produktions**-Image. Der Test gehört dorthin, wo das Image ausgeliefert
wird, und dort ist er fast kostenlos, weil er in den bestehenden Build-Job hineinpasst.

Im Framework bleibt das Muster dokumentiert: `docs/conventions/worker_image.md`, plus
der `exec celery`-Marker im `CMD`, an dem der Job den Setup-Teil abschneiden kann.
`setup_remote()` schreibt nur eine rclone-Konfigurationsdatei, braucht also kein MinIO.

**Kommando ableiten, nicht kopieren.** Eine Kopie des `CMD` in der CI-Datei wäre ein
zweiter Pflegeort, und eine grüne Kopie sagt nichts über das Kommando, das wirklich
ausgeliefert wird — also genau der Fehler eine Ebene höher. Der Job liest das `CMD` per
`docker inspect` aus dem gebauten Image.

**Was er fängt:** jeden Importpfad im `CMD`, der nicht mehr existiert. **Was er nicht
fängt:** einen falschen Worker-Befehl dahinter. Das ist der Sprung von "unentdeckbar" zu
"entdeckbar", nicht Vollständigkeit.

Das `&&` bleibt der eigentliche Fix und ist hier gesetzt.

---

## 5. Ausdrücklich NICHT in diesem Batch

- Keine Vereinheitlichung der Navbar. Die IDs bleiben, wie sie sind.
- Kein Anfassen von `app_layout()`. Cosmonauts Zwei-Panel-Shell mit der Karte ist der
  Zweck der Anwendung, nicht Duplikat.
- Kein Umbau der Exception-Hierarchie. Nur der Sentinel wandert.
- Kein `ruff format` über das Repo.

---

## 6. Definition of Done

- [x] `handle_error(error)` ohne weitere Argumente verhält sich exakt wie in `v0.6.2`.
      Ein Test, der das festhält, sonst merkt cosmonaut den Re-Pin.
- [x] `error_responses` überlagert, `expected_errors` ersetzt. Je ein Test.
- [x] Ein Test, der belegt, dass ein Eintrag mit dem Sentinel `str(error)` zeigt.
- [x] `error_responds_dict` ist im Docstring als "nicht von außen mutieren" markiert.
- [x] `create_header` ohne `id` stempelt **keine** ID. Ein Test, der das prüft, denn
      genau der Default war in beiden Apps der Bug.
- [x] `create_header(id="x")` stempelt `x`, `x-title`, `x-subtitle`.
- [x] Kein `@callback` mehr auf Modulebene in `cosmo_suite/layouts.py`.
      `register_navbar_callbacks()` existiert, ist öffentlich, idempotent und
      dokumentiert; `app_layout()` ruft sie mit.
- [x] Das `&&` im Worker-`CMD` gesetzt, `exec celery` als Marker erhalten.
- [x] Das Smoke-Muster dokumentiert in `docs/conventions/worker_image.md`, samt der
      Begründung, warum der Job in die Apps gehört. Mutationsgeprüft, nicht nur grün.
- [x] `framework_page_imports.md` hat den vierten stillen Fehlschlag.
- [x] `version = 0.7.0` in `pyproject.toml` **und** `CITATION.cff`.
- [x] `test_version.py` prüft die vier handgepflegten Versionsorte gegeneinander,
      `uv lock --check` in beiden Lint-Jobs deckt die abgeleiteten ab.
- [ ] Tag `v0.7.0` — steht noch aus, wird mit dem Commit gesetzt.

**Anmerkung zur Mutationsprüfung (2026-08-26, lokal, Docker 29.7.2).**

Das Smoke-Muster wurde als Skript gegen das wirklich gebaute Worker-Image gefahren:
unverändert Exit 0, mit verbogenem Modulpfad im `CMD` Exit 2 (`can't open file`), mit
intaktem Pfad aber kaputtem Import im Modul Exit 1 (`ModuleNotFoundError`). Die
abgeleitete Form (`docker inspect`) fängt beide; eine kopierte Form hätte die erste
Mutation nicht gefangen — deshalb steht die Ableitung so in der Konvention.

Zehn Python-Mutationen, jede fällt mit 1–3 roten Tests: `expected_errors` ergänzend
statt ersetzend · Truthiness statt `is None` · Modul-Dict-Mutation statt Kopie ·
Sentinel-Zweig entfernt · `id=""` als Default · Callback zurück auf Modulebene ·
`app_layout()` registriert nicht mehr · `CITATION.cff` zurück auf 0.6.2 · README-Pin
zurück auf v0.6.2 · Pin-Beispiel im Example entfernt.

Suiten: 59 Framework-Tests, 33 Example-Tests inklusive e2e, beide Lints, Domain-free-Gate.

---

## 7. Danach in den Apps

Eigene, kleine Slices, keine Framework-Arbeit:

- **cosmopolitan:** `error_handling.py` von 274 Zeilen auf den Rest zusammenziehen, der
  wirklich domänenspezifisch ist (die eigene Tabelle, die sechs erwarteten Fehler, der
  Mail-Hook). Lokales `create_header` löschen. `register_navbar_callbacks()` rufen, das
  ist die eine Zeile aus §3.
- **cosmonaut:** `error_responds_dict.update(...)` durch `error_responses=` ersetzen und
  den Kommentar dazu löschen.
- **Beide:** `worker-image-smoke` in den bestehenden Build-Job des Worker-Images
  aufnehmen, nach `docs/conventions/worker_image.md`. Dort ist es fast kostenlos, dort
  wird das Image ausgeliefert, und dort kann der Runner dind. Voraussetzung im `CMD`:
  `&&` statt `;` und der `exec celery`-Marker.
- **Beide:** Pin auf `v0.7.0`. Sie stehen derzeit auf `v0.6.1`, während `v0.6.2` schon
  existiert; der Unterschied ist nur das Versionslabel, deshalb kein eigener Re-Pin.

---

## 8. Die Versionsorte — erledigt, aber anders als geplant

`cosmo-suite` hat keinen Release-Job. Deshalb sind Tag, `pyproject.toml` und
`CITATION.cff` zwischen `v0.6.0` und `v0.6.2` dreifach auseinandergelaufen und mussten
von Hand gerichtet werden. Die Apps haben das Problem nicht, seit ihr Release-Job die
Versionsorte vor dem Tag schreibt.

Gemessen sind es sechs Orte, und die Einteilung entscheidet, wie der Test aussehen muss:

| Ort | Art |
|---|---|
| `pyproject.toml:3`, `CITATION.cff:23` | maßgeblich, von Hand gepflegt, muss zum Tag passen |
| `README.md:43`, `examples/csv_profiler/pyproject.toml:18` | Doku-Beispiele für den Pin eines Konsumenten, von Hand gepflegt |
| beide `uv.lock` (`version`, `source = editable`) | abgeleitet, `uv lock` schreibt sie. Kein Pflegeort |

**Warum "alle sechs gegen den letzten Tag prüfen" nicht funktioniert:** die beiden
Doku-Beispiele stehen jetzt auf `v0.7.0`, und diesen Tag gibt es noch nicht. Ein Test
gegen einen existierenden Tag schlüge genau dann fehl, wenn man einen Release
vorbereitet — der eine Moment, in dem er grün sein muss.

**Umgesetzt:** `test/test_version.py` prüft die vier handgepflegten Orte *untereinander*.
Das ist vor dem Tag prüfbar und fängt exakt den Fehler, der zweimal passiert ist. Ein
dritter Test verhindert, dass die Prüfung leerläuft, wenn ein Pin-Beispiel wegfällt. Die
abgeleiteten Orte deckt `uv lock --check` in `framework-lint` und `example-lint` ab.

---

## 9. Konventionen

`docs/conventions/error_handling.md`, `framework_page_imports.md`, `html_ids.md`,
`callbacks.md`, `testing.md`. Neu dazugekommen: `docs/conventions/worker_image.md`.

**Nicht in diesem Batch, aber gemessen:** die Konventions- und Skill-Dokumente schreiben
durchweg `src/…` statt `cosmo_suite/…` — rund 50 Stellen, verteilt auf `CLAUDE.md:70`,
sechs Konventionsdateien und vor allem die Skill-Dokumente (`convention_keeper.md` allein
20, `new_page.md` 10). Es gibt keinen einheitlichen Ersatz: im Framework heißt es
`cosmo_suite/`, im Beispiel `examples/csv_profiler/csv_profiler/`, in den Apps
`cosmopolitan_app/` bzw. `cosmonaut_app/`. Wo die Doku generisch anleitet, muss dort "das
App-Paket" stehen, kein Pfad — blind ersetzen macht es falscher. Die Skill-Dokumente sind
der teuerste Teil, weil Agenten sie als Anweisung lesen. Eigene Runde.
