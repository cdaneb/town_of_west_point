# Town of West Point
### CDTs Dane Beels and Ben Doody — CY300 Project

## Overview

Town of West Point is a Django-based Mafia web game. Players register accounts, join a lobby, and are randomly assigned roles (Town or Mafia). The game runs in timed Day/Night phases. Town members vote to eliminate suspects during the day, and Mafia picks a target to eliminate each night. The game ends when one side achieves its win condition.

The game is deployed at: **https://town-of-west-point.vercel.app**

---

## Features

- User registration and login
- Lobby with ready-up system and leave lobby option
- Random role assignment (Mafia / Town, roughly 1 Mafia per 4 players)
- Timed Day/Night phase transitions (60 seconds per phase, driven by a background timer loop)
- Game starts in Day phase — town discusses before the first vote
- Day voting to eliminate a player, with live vote tally showing who is on the execution block
- Night actions for Mafia to choose a kill target, with live targeting tally visible to Mafia
- Win detection (Town wins if all Mafia are eliminated; Mafia wins when Mafia count >= Town count)
- HTTP-polled public chat (Day phase) and Mafia-only chat (Night phase)
- Early end-game button that awards the win to whichever side has more alive players
- Game reset / new-game flow accessible from the lobby and game page
- Django admin with manual phase control and reset actions
- On-theme CSS styling (dark parchment, brass buttons, Playfair Display headings)

---

## Repo Structure

```
final_root/                                 ← git repo root
├── game/                                   ← Django app: all game logic, models, views, consumers, templates
│   ├── models.py                           ← GameState, Player, Vote, NightAction, ChatMessage
│   ├── views.py                            ← login/register/lobby/game HTTP endpoints + chat API
│   ├── phase_change.py                     ← phase transitions, win detection, game reset
│   ├── role_assignment.py                  ← random role assignment
│   ├── consumers.py                        ← WebSocket consumers (legacy, not used in deployment)
│   ├── routing.py                          ← WebSocket URL routing (legacy)
│   ├── admin.py                            ← admin registration + manual phase control actions
│   ├── urls.py                             ← app URL routing
│   ├── management/
│   │   └── commands/
│   │       └── run_game_timer.py           ← background timer loop command
│   ├── tests.py                            ← 27 pytest tests covering all game scenarios
│   ├── static/game/
│   │   ├── style.css                       ← on-theme CSS (dark parchment, brass, phase classes)
│   │   └── game.js                         ← countdown timer, chat polling, lantern animation
│   └── templates/game/                     ← login, register, lobby, game HTML templates
├── mvp/                                    ← Django project package (settings, urls, asgi, wsgi)
├── staticfiles/                            ← collected static files (committed for Vercel serving)
├── manage.py                               ← Django management entrypoint
├── db.sqlite3                              ← local SQLite database (dev/testing only)
├── requirements.txt
├── vercel.json                             ← Vercel deployment config
├── build_files.sh                          ← Vercel build script
├── pytest.ini                              ← pytest configuration
├── DEPLOYMENT_NOTES.md                     ← deployment architecture and known limitations
└── .env.example                            ← template for required environment variables
```

---

## Local Setup

**Prerequisites:** Python 3.11+

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows (if execution policy error arises)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. (Optional) Create a Django superuser for admin access
python manage.py createsuperuser
```

---

## Running the Game Locally

The game requires **two processes** running simultaneously:

### Terminal 1 — Run server
```bash
daphne mvp.asgi:application
```

This will run the game in the browser at `127.0.0.1:8000`.

> You can also use `python manage.py runserver` for basic testing, but WebSocket consumers require Daphne or another ASGI server.

### Terminal 2 — Run phase timer loop
```bash
python manage.py run_game_timer
```

This loop checks every second whether the current phase timer has expired and advances the game (Day → Night → Day) accordingly.

---

## Running Against the Deployed Database (Vercel + Neon)

To host a live game on the deployed site, the phase timer must be run locally pointing at the production Neon Postgres database. Open a terminal with the virtual environment activated and set the following environment variables before starting the timer:

### Windows (PowerShell)
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\activate
$env:DATABASE_URL="postgresql://neondb_owner:<password>@ep-little-bonus-amx064h1-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"
$env:SECRET_KEY="<your-secret-key>"
$env:DEBUG="False"
$env:DJANGO_SETTINGS_MODULE="mvp.settings"
python manage.py run_game_timer
```

### macOS/Linux
```bash
source .venv/bin/activate
export DATABASE_URL="postgresql://neondb_owner:<password>@ep-little-bonus-amx064h1-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"
export SECRET_KEY="<your-secret-key>"
export DEBUG="False"
export DJANGO_SETTINGS_MODULE="mvp.settings"
python manage.py run_game_timer
```

Keep this terminal open for the duration of any live game session. Closing it will cause phases to stop advancing.

---

## Gameplay Flow

1. All players register accounts at `/register/` and log in.
2. In the lobby (`/lobby/`), each player clicks **Ready Up**.
3. Any player clicks **Start Game** (requires at least 2 ready players).
4. Roles are assigned randomly (roughly 1 Mafia per 4 players).
5. The game begins in **Day** phase. All alive players can vote and use public chat. A live vote tally shows who is currently on the execution block.
6. After 60 seconds, the most-voted player is eliminated and the phase advances to **Night**. Mafia players see a target button, a private Mafia chat, and a tally of which Town player is most targeted.
7. Phases alternate until a win condition is met, or any player clicks **End Game** to force an immediate result.
8. When the game ends, roles are revealed and any player can click **Return to Lobby** to start a new round.

---

## Admin / Debug

Visit `/admin/` with a superuser account to:
- Manually advance the game phase
- Reset the game to LOBBY at any time
- Inspect all models (GameState, Player, Vote, NightAction, ChatMessage)

---

## Testing

```powershell
# Windows
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\activate
$env:PYTHONPATH = "."
$env:DJANGO_SETTINGS_MODULE = "mvp.settings"
python -m pytest game/tests.py -v
```

```bash
# macOS/Linux
source .venv/bin/activate
PYTHONPATH=. DJANGO_SETTINGS_MODULE=mvp.settings python -m pytest game/tests.py -v
```

The test suite covers 27 scenarios including: registration/login, lobby flow, role assignment, phase transitions, day voting, night actions, win detection, double-vote prevention, and game reset.

If the project is moved to a new machine, recreate the virtual environment:
```bash
python -m venv .venv
```

---

## Deployment

The site is deployed on **Vercel** using a WSGI build (`mvp/wsgi.py`). The database is hosted on **Neon** (Postgres) and static files are served via **WhiteNoise**.

Required environment variables (set in Vercel dashboard):

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Set to `False` in production |
| `DATABASE_URL` | Neon Postgres connection string |
| `REDIS_URL` | Upstash Redis URL (for channel layer) |
| `ALLOWED_HOSTS` | `town-of-west-point.vercel.app` |

See `DEPLOYMENT_NOTES.md` for full architecture notes and known limitations.

---

## Known Limitations

- **Phase timer:** The background timer (`run_game_timer`) cannot run on Vercel's serverless platform. It must be run locally by a host machine for the duration of each game session.
- **Player count:** A minimum of 2 ready players is enforced. For actual gameplay, 5+ players is recommended.
- **Single game instance:** There is only ever one active `GameState` (id=1). All registered users share the same game. There is no multi-game or spectator support.
- **Chat:** WebSocket chat is not supported on Vercel. Chat uses HTTP polling (2-second interval) instead.
- **No persistent game history:** Resetting the game deletes all chat messages, votes, and night actions from the current round.