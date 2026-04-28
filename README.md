# Town of West Point
### CDTs Christian Beels and Benjamin Doody — CY300 Project

## Overview

Town of West Point is a Django-based Mafia web game. Players register accounts, join a lobby, and are randomly assigned roles (Town or Mafia). The game runs in timed Day/Night phases. Town members vote to eliminate suspects during the day, and Mafia picks a target to eliminate each night. The game ends when one side achieves its win condition.

---

## Features

- User registration and login
- Lobby with ready-up system
- Random role assignment (Mafia / Town)
- Timed Day/Night phase transitions (2 minutes per phase, driven by a background timer loop)
- Day voting to eliminate a player
- Night actions for Mafia to choose a kill target
- Win detection (Town wins if all Mafia are eliminated; Mafia wins when Mafia count >= Town count)
- Live public chat via WebSocket (Day phase)
- Live Mafia-only chat via WebSocket (Night phase, Mafia players only)
- Early end-game button that awards the win to whichever side has more alive players
- Game reset / new-game flow accessible from the lobby and game page
- Django admin with manual phase control and reset actions

---

## Repo Structure

```
mvp/                                        ← git repo root
├── game/                                   ← Django app: all game logic, models, views, consumers, templates
│   ├── models.py                           ← GameState, Player, Vote, NightAction, ChatMessage
│   ├── views.py                            ← login/register/lobby/game HTTP endpoints
│   ├── phase_change.py                     ← phase transitions, win detection, game reset
│   ├── role_assignment.py                  ← random role assignment
│   ├── consumers.py                        ← WebSocket consumers for public and Mafia chat
│   ├── routing.py                          ← WebSocket URL routing
│   ├── admin.py                            ← admin registration + manual phase control actions
│   ├── urls.py                             ← app URL routing
│   ├── management/
│   │   └── commands/
│   │       └── run_game_timer.py           ← background timer loop command
|   |-- tests.py                            <- tests game timer and double votes
│   └── templates/game/                     ← login, register, lobby, game HTML templates
├── mvp/                                    ← Django project package (settings, urls, asgi, wsgi)
├── manage.py                               ← Django management entrypoint
├── db.sqlite3                              ← local SQLite database (dev/testing)
└── requirements.txt
```

---

## Local Setup

**Prerequisites:** Python 3.11+

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows
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

## Running the Game

The game requires **two processes** running simultaneously:

### Terminal 1 — Run server
```bash
daphne mvp.asgi:application
```

This will run the game in the browser at 127.0.0.1:8000 .

> You can also use `python manage.py runserver` for basic testing, but WebSocket chat requires Daphne or another ASGI server.

### Terminal 2 — Run Phase timer loop
```bash
python manage.py run_game_timer
```

This loop checks every second whether the current phase timer has expired and advances the game (Night → Day → Night) accordingly.

---

## Gameplay Flow

1. All players register accounts at `/register/` and log in.
2. In the lobby (`/lobby/`), each player clicks **Ready Up**.
3. Any player clicks **Start Game** (requires at least 2 ready players).
4. Roles are assigned randomly (roughly 1 Mafia per 4 players).
5. The game begins in **Night** phase. Mafia players can see a target button and a private Mafia chat.
6. After 2 minutes, the phase advances to **Day**. All alive players can vote and use public chat.
7. Phases alternate until a win condition is met, or any player clicks **End Game** to force an immediate result.
8. When the game ends, any player can click **Return to Lobby** to start a new round.

---

## Admin / Debug

Visit `/admin/` with a superuser account to:
- Manually advance the game phase
- Reset the game to LOBBY at any time
- Inspect all models (GameState, Player, Vote, NightAction, ChatMessage)

---

## Known Limitations

- **Player count:** A minimum of 2 ready players is enforced. For actual gameplay, 5+ players is recommended. A 2-player game (1 Mafia, 1 Town) will end in a Mafia win after the first Night if no kill action is taken.
- **Single game instance:** There is only ever one active `GameState` (id=1). All registered users share the same game. There is no multi-game or spectator support.
- **WebSocket channel layer:** Uses Django Channels' in-memory channel layer. WebSocket chat works only within a single server process. For multi-process or production deployments, configure a Redis channel layer.
- **Local development only:** `DEBUG=True`, `ALLOWED_HOSTS=[]`, and SQLite are configured for local use. Do not deploy as-is to production.
- **No persistent game history:** Resetting the game deletes all chat messages, votes, and night actions from the current round.

---
## Testing
- use pip to install library "pytest-django"
- Ensure all dependencies are installed in the virtual environment.
-- pip install pytest pytest-django daphne channels
- If on windows, this may be required to activate scrips if an access error arises:
-- Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
- Navigate to project root and run:
-- $env:PYTHONPATH = "."; $env:DJANGO_SETTINGS_MODULE = "mvp.settings"; python -m pytest game/tests.py
- If project is moved between computers, run this for pathing issues:
-- python -m venv .venv