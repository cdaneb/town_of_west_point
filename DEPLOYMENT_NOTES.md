# Deployment Notes — Town of West Point

## Live URL

Deployed at: https://town-of-west-point.vercel.app  
*(Update this once Vercel assigns a final URL)*

---

## Known Limitations

### Phase Timer (`run_game_timer.py`)

The background management command `game/management/commands/run_game_timer.py` runs a loop
that automatically advances game phases when the timer expires. **This cannot run on
Vercel's serverless platform** because serverless functions are stateless and short-lived.

**Workarounds:**
- The game page polls `/api/state/` every 2 seconds and reloads when the phase changes, so
  players see transitions. But the server-side phase advance must be triggered externally.
- Use **Vercel Cron Jobs** (`vercel.json` `crons` field) to POST to a protected webhook
  endpoint that calls `advance_if_timer_expired()`.
- Alternatively, run the timer command on a small VPS or via GitHub Actions on a schedule.

### WebSocket Chat

Chat uses Django Channels WebSocket consumers (`game/consumers.py`). Vercel's serverless
functions **do not support persistent WebSocket connections**.

**Current behavior on Vercel:** The HTTP game layer (voting, phase transitions, role display)
works fully. WebSocket chat will fail to connect; the browser console will log a warning and
the game degrades gracefully — polling-based phase updates still work.

**To enable full chat:** Deploy the ASGI server (Daphne) on a persistent host (e.g., a
Fly.io container, Railway, or a VPS) and set `REDIS_URL` so the channel layer is shared
across processes. The settings already support this — just set the environment variable.

### Database

Vercel Postgres (or Neon/Supabase) is used in production via the `DATABASE_URL` env var.
SQLite is used for local development when `DATABASE_URL` is not set.

After any new migration, run:
```bash
vercel env pull .env.local && python manage.py migrate
```

### Environment Variables Required on Vercel

| Variable       | Description                                      |
|----------------|--------------------------------------------------|
| `SECRET_KEY`   | Django secret key (generate a new random value)  |
| `DEBUG`        | Set to `False` in production                     |
| `DATABASE_URL` | Postgres connection string                       |
| `REDIS_URL`    | Redis connection string (Upstash recommended)    |
| `ALLOWED_HOSTS`| Vercel domain, e.g. `town-of-west-point.vercel.app` |
