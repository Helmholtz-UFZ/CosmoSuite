# Slice 1 — Framework-Batch (Tag 1)

**Repo:** `cosmo-suite` · **Branch:** neu, `slice1-framework-batch` off `main` (`56c8e33`)
**Ziel-Tag am Ende:** `v0.3.0` · **Erstellt:** 2026-08-05

---

## 0. Warum dieser Batch existiert

Fig. 2b des SoftwareX-Drafts behauptet, COSMOPOLITAN und COSMONAUT teilen dieses
Framework. Gemessen am 2026-08-05: **null Importe** in beiden Apps. Slice 1 macht die
Behauptung wahr, indem beide Apps ~2.500–2.700 Zeilen Infrastruktur aus `cosmo_suite`
importieren statt sie zu duplizieren.

Dieser Batch geht **allen App-Arbeiten voraus**. Danach wird das Framework getaggt und
für die Dauer von Slice 1 **eingefroren**. Zwei App-Agenten arbeiten parallel gegen den
Tag; ein wandernder Unterbau würde sie gegeneinander debuggen lassen.

**Freeze-Regel:** Braucht ein App-Agent während Slice 1 eine Framework-Änderung, ist das
ein eigener MR hier, ein neuer Tag, und **beide** Apps re-pinnen. Keine stillen Edits am
Framework, während die App-Agenten laufen.

---

## 1. Aufgabe 1 — `get_presigned_download_url` aufnehmen

Cosmonaut hat in `cosmonaut_app/object_storage_manager.py` eine Funktion, die das
Framework nicht hat: eine presigned GET-URL für den QR-Code-Download außerhalb des
Netzes. Das ist der **einzige echte Funktionsunterschied** in diesem Modul — die
gemessenen 268 Diff-Zeilen sind ansonsten Docstrings, Trailing Commas und die Ablage der
Exception-Klasse.

Sie ist das erste Feature, das das Framework von einem *zweiten* Consumer aufnimmt.
Genau das ist der Beweis, den das Paper braucht.

**Schritte:**

1. `get_presigned_download_url(object_key: str, expiry: timedelta) -> str` nach
   `cosmo_suite/object_storage_manager.py` übernehmen. Quelle:
   `../ufz-cosmonaut/cosmonaut_app/object_storage_manager.py`.
2. `"minio>=7.2.0,<8"` zu `[project].dependencies` in `pyproject.toml` hinzufügen.
   Cosmonaut pinnt bereits genau diesen Range — keine Kollision zu erwarten.
3. `uv lock`.
4. Die Funktion baut ihren `Minio`-Client aus `OBJECT_STORAGE_HOST/_ACCESS_KEY/
   _SECRET_KEY/_BUCKET`. Alle vier exportiert `cosmo_suite/config.py` bereits — nichts
   Neues nötig.
5. Sie wirft `ObjectStorageError`. Die Klasse ist in diesem Modul definiert
   (`object_storage_manager.py:21`) — Import bleibt lokal, kein Zyklus.

---

## 2. Aufgabe 2 — `ObjectStorageError` bleibt, wo sie ist (Entscheidung dokumentieren)

Gemessene Lage:

| Baum | `class ObjectStorageError` steht in |
|---|---|
| Framework | `object_storage_manager.py:21` |
| cosmopolitan | `object_storage_manager.py:21` — **identisch** |
| cosmonaut | `error_handling.py:44` — **abweichend** |

**Entscheidung: nicht verschieben.** Gründe:

- Cosmopolitan stimmt schon überein; ein Verschieben würde ohne Not zwei Consumer statt
  einem anfassen.
- Ein Verschieben nach `cosmo_suite/error_handling.py` zöge `error_handling` in Slice 1,
  und das ist bewusst draußen (§5).

Konsequenz für cosmonaut, in dessen Handoff festgehalten: dort wird die lokale Klasse
durch einen Re-Export ersetzt. **Ohne den greifen cosmonauts `except
ObjectStorageError`-Blöcke nicht mehr — die Framework-Funktionen werfen eine andere
Klasse gleichen Namens. Das ist ein stiller Fehlschlag, kein Importfehler.**

Nichts zu tun in diesem Batch außer: einen Kommentar an die Klasse setzen, dass sie
absichtlich hier und nicht in `error_handling` lebt (Konventionsphilosophie aus
`CLAUDE.md`: Abweichung mit Begründung).

---

## 3. Aufgabe 3 — ID-Namenskonflikt entscheiden

| Framework | cosmonaut |
|---|---|
| `LOADING_OVERLAY_MODAL_SHARED_ID` | `LOADING_OVERLAY_SHARED_ID` |

**Framework-Name gewinnt.** Cosmopolitan verwendet ihn bereits; nur cosmonaut zieht nach
(23 Fundstellen über 8 Dateien, davon 2 Testdateien — Liste im cosmonaut-Handoff).

Nichts zu ändern im Framework. Nur hier festhalten, damit die Entscheidung nicht in
jedem der beiden App-Agenten neu verhandelt wird.

Zur Kenntnis für den cosmopolitan-Agenten (dort ausgeführt, nicht hier): sechs weitere
Konstanten heißen in cosmopolitan anders (`REFRESH_BUTTON_WORKER_MANAGEMENT_ID` →
`WORKER_REFRESH_BTN_WORKER_MANAGEMENT_ID` usw.). Dabei ändern sich auch die **Werte**
(`refresh-button-…` → `worker-refresh-btn-…`), also brechen Playwright-Locators.

---

## 4. Aufgabe 4 — Version geradeziehen und taggen

`pyproject.toml` sagt `version = "0.1.0"`, aber Tags `v0.1.0` **und** `v0.2.0`
existieren. Ein Pin auf `@v0.2.0` installiert damit ein Paket, das sich als `0.1.0`
meldet. Das läuft sonst in C1 der Metadaten-Tabelle des Papers nach ("Current code
version — for Suite and the apps").

1. `version = "0.3.0"` setzen. **0.2.x überspringen** — der Nummernraum ist durch den
   Mismatch verbrannt, und beide Apps sollen unmissverständlich pinnen.
2. Nach Merge auf `main`: `git tag v0.3.0 && git push --tags`.
3. Beide App-Handoffs pinnen auf:
   ```toml
   "cosmo-suite @ git+https://codebase.helmholtz.cloud/ufz/tb5-smm/met/wg7/cosmo-suite@v0.3.0",
   ```

---

## 4b. Aufgabe 5 (Nachtrag bei der Ausführung) — `Job.app_version`-Seam

Bei Aufgabe 4 aufgefallen: `cosmo_suite/job.py` hatte `APP_VERSION = "0.1.0"`
hartkodiert und stempelte das in die `version`-Spalte **jedes** Jobs. Das ist
semantisch die Version der *App*, nicht des Frameworks — beide Apps hätten alle ihre
Jobs mit `0.1.0` beschriftet, unabhängig von ihrem eigenen Stand. Derselbe
Zahlen-Mismatch wie in Aufgabe 4, nur eine Ebene tiefer, und ebenfalls relevant für
C1 der Metadaten-Tabelle.

Bewusst **vor** dem Tag erledigt: danach kostet es beide Apps ein Re-Pin.

- `FRAMEWORK_VERSION` kommt jetzt aus der Distribution-Metadata
  (`importlib.metadata.version("cosmo-suite")`), kann also nicht mehr von
  `pyproject.toml` abdriften. Fallback `"unknown"` bei `PackageNotFoundError`
  (PYTHONPATH-Nutzung ohne Installation) — bewusst keine plausible Zahl.
- Vierter Seam: `Job.app_version`, Default `FRAMEWORK_VERSION`. Optional, kein
  Fail-loud. Dokumentiert in `docs/conventions/config_model_contract.md`.
- **Für beide App-Agenten:** `Job.app_version = version("<app-paket>")` setzen, und
  zwar in `app.py` **und** `celery_app.py` — ein ungesetzter Seam im Worker stempelt
  still die Framework-Version. Referenz: `examples/csv_profiler/csv_profiler/app.py`
  und `celery_app.py`.

---

## 5. Ausdrücklich NICHT in diesem Batch

**Der `on_unhandled`-Hook für `handle_error`.** Beide Apps mailen bei unbehandelten
Fehlern an `MAINTAINER_EMAIL` (`cosmopolitan_app/error_handling.py:253`,
`cosmonaut_app/error_handling.py:169`); das Framework loggt nur. Der Hook wird gebraucht
— aber `error_handling` ist aus Slice 1 heraus, weil `handle_error` überall importiert
wird und verlorene Maintainer-Mails **still** ausfallen. Das ist Slice 2.

Ebenfalls draußen: `DomainPlugin`-Protokoll, Plugin-Registry, Branding-Layer aus
`framework-generalization.md` — davon ist nichts implementiert und nichts davon braucht
das Paper.

---

## 6. Verifikation (Definition of Done)

Das Framework hat außer `test/test_html_id_enforcement.py` **keine eigene Suite**. Der
einzige echte Prüfstand ist das Beispiel:

```bash
cd examples/csv_profiler && ./run_pytest.sh      # muss grün bleiben
cd /home/trinkle/git/cosmo-suite
uv run ruff format --check cosmo_suite test
uv run ruff check cosmo_suite test
grep -rnE --include='*.py' 'csv_profiler|ProfileConfig|computation_module|validate_csv|profile_csv|CSV_UPLOAD' cosmo_suite/   # muss leer sein (CI-Gate)
```

Fertig heißt: Beispielsuite grün, `ruff` sauber, `domain-free`-Gate leer, `v0.3.0`
getaggt und gepusht, beide App-Handoffs referenzieren den Tag.

---

## 7. Konventionen

`CLAUDE.md` gilt: keine `dict.get()`, kein bare `except Exception`, keine Inline-Imports,
HTML-IDs nur aus `cosmo_suite/constants/html_ids.py`, kein Inline-CSS. Abweichung ist
erlaubt — mit Kommentar, der sie begründet.
