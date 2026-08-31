# Debugging Guide

Set breakpoints and step through the running API or the test suite. Files:

| File | Role |
|------|------|
| `.vscode/launch.json` | Debug/run configurations (VS Code, "Run and Debug" panel). |
| `.vscode/settings.json` | Enables the pytest Test Explorer; points VS Code at `.env.debug`. |
| `.env.debug` | Env vars for host-side debugging (points the DB host at `127.0.0.1`). |
| `docker-compose.debug.yml` | Runs the container under `debugpy` for attach-mode debugging. |

---

## Prerequisites (one time)

1. **VS Code** with the **Python** + **Python Debugger** extensions.
2. A virtualenv with the dev dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\Activate.ps1        # Windows PowerShell
   pip install -r requirements-dev.txt
   ```
3. Select that interpreter in VS Code: `Ctrl+Shift+P` -> **Python: Select Interpreter** -> `.\venv\Scripts\python.exe`.
4. Start **only Postgres** (published on `localhost:5432` by `docker-compose.yml`):
   ```bash
   docker compose up -d db
   docker compose run --rm web python manage.py migrate   # first run only
   ```

> No local PostgreSQL install needed - the debugger runs on the host and talks to
> the Dockerised database over the published port. If you *do* have a native
> Postgres on 5432, stop the `db` container or change `POSTGRES_PORT` in `.env.debug`.

---

## Workflow A - launch & debug locally (recommended)

The debugger starts the process, so breakpoints work with zero extra setup.

1. Open the **Run and Debug** panel (`Ctrl+Shift+D`).
2. Pick a configuration from the dropdown:

   | Configuration | Use it to |
   |---------------|-----------|
   | **Django: runserver** | Debug real HTTP requests. Auto-reload on. |
   | **Django: runserver (no autoreload)** | Same, but rock-solid breakpoints (use if the reload variant ever skips a breakpoint). |
   | **Django: shell** | Poke at the ORM with breakpoints in an interactive shell. |
   | **Pytest: all tests** | Debug the whole suite. |
   | **Pytest: current file** | Debug the test file that's open in the editor. |

3. Set a breakpoint (click the gutter, or put `breakpoint()` in the code).
4. Press **F5**.
5. For the server configs, send a request (curl, Postman, browser). Execution stops
   at the breakpoint; use **F10** step over, **F11** step into, **F5** continue, and
   the **Debug Console** to evaluate expressions (`request.query_params`,
   `queryset.query`, `serializer.data`, ...).

`justMyCode` is set to `false` in every config, so **F11** steps into Django and
DRF source too - handy for seeing exactly which SQL the Ride List view builds.

### Debugging a single test

With `.vscode/settings.json` in place, open the **Testing** panel (beaker icon):
every test has a **Debug Test** (play-with-bug) button. Or open a test file and run
**Pytest: current file**. Add `-k name_fragment` to `args` in `launch.json` to
narrow it further.

---

## Workflow B - attach to the container

Use this when you want to debug the app exactly as it runs in Docker.

1. Start the stack with the debug override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.debug.yml up
   ```
   The web container installs `debugpy`, then **waits** - it prints
   `... waiting for client` and does not serve requests yet.
2. In VS Code pick **Attach: Docker web (debugpy :5678)** and press **F5**.
3. The server finishes starting. Set breakpoints and hit the API on
   `http://localhost:8000`. `pathMappings` maps the container's `/app` to your
   workspace so breakpoints line up.
4. Stop with `Ctrl+C` in the compose terminal.

To make it permanent, add `debugpy>=1.8` to `requirements-dev.txt` and drop the
`pip install` from `docker-compose.debug.yml`.

---

## Good places to put a breakpoint

| Question | File / line |
|----------|-------------|
| How is the 24 h window + join/prefetch built? | `rides/views.py` -> `RideViewSet.get_queryset` |
| What SQL / how many queries? | same method - inspect `str(queryset.query)`; or breakpoint in a test using `django_assert_max_num_queries` |
| Why did an `ordering` value 400? | `rides/ordering.py` -> `RideOrderingFilter.filter_queryset` / `_parse_coordinates` |
| Distance annotation expression | `rides/distance.py` -> `annotate_distance` |
| Why is `distance_km` present / absent? | `rides/serializers.py` -> `RideListSerializer` |
| Filter not matching? | `rides/filters.py` -> `RideFilter` |
| 401 vs 403 | `accounts/permissions.py` -> `IsAdminRole.has_permission` |
| Password handling | `accounts/serializers.py` -> `UserSerializer.create` / `update` |

---

## No-IDE fallback (pdb)

```bash
# stop on failure and drop into pdb
pytest --pdb

# start pdb at the top of every selected test
pytest --trace -k ride_list_query_budget

# debug the server
python manage.py runserver --noreload      # then add breakpoint() in the code
```

`breakpoint()` anywhere in the code opens `pdb` in the terminal running the process
(`n` next, `s` step, `c` continue, `p expr` print, `q` quit).

---

## Note on version control

`.vscode/` and `.env.debug` are safe to commit (no secrets) and document the setup
for a reviewer. If you'd rather keep them local, add these lines to `.gitignore`:

```gitignore
.vscode/
.env.debug
docker-compose.debug.yml
```
