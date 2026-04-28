# Claude Code Instructions — Town of West Point

## Project Context

This is a Django-based Mafia web game. The root directory for all work is:

```
C:\Users\christian.beels\OneDrive - West Point\AYfiles\2026_2\CY300\project\Final Code Submission\final\final_root
```

The project structure inside that root matches the `mvp/` layout described in the README:

```
mvp/
├── game/
│   ├── models.py
│   ├── views.py
│   ├── phase_change.py
│   ├── role_assignment.py
│   ├── consumers.py
│   ├── routing.py
│   ├── admin.py
│   ├── urls.py
│   ├── management/commands/run_game_timer.py
│   ├── tests.py
│   └── templates/game/
├── mvp/           ← Django project package (settings, urls, asgi, wsgi)
├── manage.py
├── db.sqlite3
└── requirements.txt
```

Work through all four tasks below in order. Do not skip ahead — each task may depend on the previous one.

---

## Task 1 — Debug and Test with PyTest

### Goal
Ensure all game functions work correctly. Fix any bugs discovered.

### Steps

1. **Set up the test environment.** From the project root (`mvp/`), run:
   ```bash
   pip install pytest pytest-django daphne channels
   ```

2. **Confirm `pytest.ini` or `setup.cfg` exists** with Django settings configured. If it does not exist, create `pytest.ini` at the project root with:
   ```ini
   [pytest]
   DJANGO_SETTINGS_MODULE = mvp.settings
   ```

3. **Run the existing tests** to establish a baseline:
   ```bash
   cd mvp
   python -m pytest game/tests.py -v
   ```

4. **Review failures.** For each failing test, inspect the relevant source file (`models.py`, `views.py`, `phase_change.py`, `role_assignment.py`, `consumers.py`) and fix the underlying bug. Do not simply delete or skip failing tests.

5. **Expand test coverage.** Add tests to `game/tests.py` for any of the following that are not already covered:
   - User registration and login (valid and invalid credentials)
   - Lobby ready-up flow and Start Game trigger
   - Role assignment (correct ratio of ~1 Mafia per 4 players; no player left without a role)
   - Phase transitions: Night → Day → Night via `phase_change.py`
   - Day voting: a player receives enough votes and is eliminated
   - Night action: Mafia submits a kill target; target is eliminated at phase transition
   - Win detection: Town wins when all Mafia are eliminated; Mafia wins when Mafia count ≥ Town count
   - Double-vote prevention (already referenced in `tests.py` — verify it passes)
   - Game reset clears all votes, night actions, and chat messages
   - Early end-game button correctly awards the win

6. **Run the full suite again** and confirm all tests pass before moving on:
   ```bash
   python -m pytest game/tests.py -v
   ```

7. **Known limitations to be aware of** (do not attempt to fix these unless explicitly instructed):
   - In-memory channel layer — WebSocket chat only works in a single server process
   - Single `GameState` instance (id=1) — no multi-game support
   - SQLite is used for local testing; this will be replaced in Task 3

---

## Task 2 — Push Source to GitHub

### Goal
Push all project source files to the empty repository at `https://github.com/cdaneb/town_of_west_point.git`.

### Steps

1. **Add a `.gitignore`** at the project root if one does not exist. At minimum it should exclude:
   ```
   .venv/
   __pycache__/
   *.pyc
   db.sqlite3
   *.env
   .env
   staticfiles/
   ```

2. **Add a `.env.example`** file documenting any environment variables used in `mvp/settings.py` (e.g., `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL`). Do not commit real secrets.

3. **Ensure `mvp/settings.py` reads secrets from environment variables** rather than hardcoding them. Use `os.environ.get(...)` or the `python-decouple` / `django-environ` pattern. The `SECRET_KEY` and `DEBUG` values must be environment-variable-driven before the code is pushed.

4. **Initialize git and push:**
   ```bash
   cd <project_root>   # the directory containing mvp/ and manage.py
   git init
   git remote add origin https://github.com/cdaneb/town_of_west_point.git
   git add .
   git commit -m "Initial commit — Town of West Point"
   git branch -M main
   git push -u origin main
   ```

5. **Verify** the repository at `https://github.com/cdaneb/town_of_west_point` shows all expected files matching the structure in the README.

---

## Task 3 — Deploy to Vercel

### Important notes before starting

- Vercel is a Node.js/serverless platform. Django with Daphne (ASGI/WebSocket) does **not** deploy natively to Vercel's serverless functions. The correct approach is:
  - Deploy the **Django HTTP layer** to Vercel using `vercel-python` (WSGI/ASGI adapter).
  - WebSocket consumers (`consumers.py`) require a persistent server — Vercel cannot run these. Migrate WebSocket support to use a **Redis channel layer** so that if a separate WebSocket-capable host is needed in future, it is already compatible.
  - For the scope of this deployment, note this limitation in a `DEPLOYMENT_NOTES.md` file and configure the game to degrade gracefully (chat disabled) if WebSockets are unavailable.

- The SQLite database must be replaced for multi-user deployment. Use **Vercel Postgres** (or any external Postgres provider such as Neon or Supabase) so that data persists across serverless invocations.

### Steps

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Switch the database to Postgres.** Add `psycopg2-binary` and `dj-database-url` to `requirements.txt`. Update `mvp/settings.py`:
   ```python
   import dj_database_url, os
   DATABASES = {
       'default': dj_database_url.config(
           default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
       )
   }
   ```

3. **Switch the channel layer to Redis** (required for WebSocket support beyond a single process). Add `channels-redis` to `requirements.txt`. Update `mvp/settings.py`:
   ```python
   CHANNEL_LAYERS = {
       "default": {
           "BACKEND": "channels_redis.core.RedisChannelLayer",
           "CONFIG": {"hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379")]},
       }
   }
   ```

4. **Create `vercel.json`** at the project root:
   ```json
   {
     "builds": [
       { "src": "mvp/wsgi.py", "use": "@vercel/python" }
     ],
     "routes": [
       { "src": "/(.*)", "dest": "mvp/wsgi.py" }
     ]
   }
   ```

5. **Add a `build_files.sh`** script (run during Vercel build) to collect static files:
   ```bash
   #!/bin/bash
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```
   Reference it in `vercel.json` under `"installCommand"` or as a build hook as appropriate.

6. **Set environment variables in Vercel** (via the Vercel dashboard or CLI) before deploying:
   - `SECRET_KEY`
   - `DEBUG` = `False`
   - `DATABASE_URL` (from your Postgres provider)
   - `REDIS_URL` (from your Redis provider, e.g. Upstash)
   - `ALLOWED_HOSTS` = your Vercel deployment domain (e.g. `town-of-west-point.vercel.app`)

7. **Deploy:**
   ```bash
   vercel --prod
   ```

8. **Run migrations on the remote database** after the first deploy:
   ```bash
   vercel env pull .env.local
   python manage.py migrate
   ```

9. **Create `DEPLOYMENT_NOTES.md`** at the project root documenting:
   - The live Vercel URL
   - That the background phase timer (`run_game_timer.py`) cannot run on Vercel's serverless platform and must be run separately (e.g., on a VPS or via a cron job service such as Vercel Cron or GitHub Actions)
   - That WebSocket chat requires a Redis-backed channel layer and a persistent ASGI server if full chat functionality is needed

---

## Task 4 — Minimal On-Theme CSS/JS Styling

### Goal
Add visual polish to the four game templates while keeping the aesthetic consistent with the Mafia/Town-of-West-Point theme (dark night sky, lantern glow, old-west textures).

### Files to style
All templates are located at `game/templates/game/`. Apply a **shared base stylesheet** rather than per-template inline styles.

### Steps

1. **Create `game/static/game/style.css`** (and add `game/static/` to Django's `STATICFILES_DIRS` or ensure the app is in `INSTALLED_APPS` so static files are picked up). Write CSS that:

   - Sets a dark background (`#1a1209` or similar deep brown-black) with off-white text (`#f0e6c8`) to evoke candlelit parchment.
   - Uses a serif or slab-serif Google Font (e.g., `Playfair Display` or `Josefin Slab`) for headings and a legible sans-serif for body text.
   - Styles buttons as aged brass/copper (`background: #8b6914`, `border: 2px solid #c49a22`) with a hover glow effect.
   - Adds a subtle texture or border to card/panel elements (a faint `box-shadow` in amber tones is sufficient).
   - Styles the Day phase with a warm amber tint on panel backgrounds, and the Night phase with a cooler, darker slate tint — apply these via a `.phase-day` / `.phase-night` class on the `<body>` tag, driven by a template variable already available in views.
   - Makes the layout responsive (flexbox or CSS grid) so it works on multiple screen sizes for simultaneous players.

2. **Create `game/static/game/game.js`** with minimal JavaScript:

   - A subtle "flicker" animation on any element with class `.lantern` (use CSS `@keyframes` triggered by JS adding the class on page load).
   - Auto-scroll the chat window to the bottom on new messages (if the chat container has id `chat-log`, attach a `MutationObserver`).
   - A countdown timer display: read a `data-phase-end` attribute (Unix timestamp, set in the template from the `GameState` model) and update a `<span id="phase-timer">` every second showing `MM:SS` remaining in the current phase.

3. **Update each template** (`login.html`, `register.html`, `lobby.html`, `game.html`) to:
   - `{% load static %}` and link `style.css` and `game.js`.
   - Add the `.phase-day` or `.phase-night` class to `<body>` where appropriate.
   - Add a `<span class="lantern">🕯</span>` decorative element in the header.
   - Pass `data-phase-end="{{ game_state.phase_end_time|date:'U' }}"` on the timer element in `game.html`.

4. **Run `collectstatic`** locally and confirm the styles appear correctly before committing:
   ```bash
   python manage.py collectstatic --noinput
   daphne mvp.asgi:application
   ```

5. **Commit and push** the static files and updated templates to GitHub, then redeploy to Vercel.

---

## Final Checklist

Before considering all tasks complete, verify:

- [ ] All PyTest tests pass with `python -m pytest game/tests.py -v`
- [ ] GitHub repo at `https://github.com/cdaneb/town_of_west_point` contains all source files and a `.gitignore`
- [ ] No secrets (`SECRET_KEY`, passwords, API keys) are committed to the repo
- [ ] The site is live and accessible at the Vercel deployment URL
- [ ] Multiple users can register, join the lobby, and play a game simultaneously
- [ ] All four templates render with the on-theme CSS styling
- [ ] The phase countdown timer displays correctly in `game.html`
- [ ] `DEPLOYMENT_NOTES.md` documents known limitations (phase timer, WebSocket caveats)
