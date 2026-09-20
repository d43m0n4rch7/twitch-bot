# Deployment

Sets up the bot on a VPS behind Caddy, as a systemd service, with GitHub
Actions deploying automatically on every push to `main`.

Assumes Ubuntu/Debian and that you have root (or sudo) access to the VPS,
and that Caddy is already installed (`sudo apt install caddy` or the
official repo — see https://caddyserver.com/docs/install).

All application files and the long-running process belong to the **`twitchbot`**
system user under `/opt/twitch-bot`.

## 1. Create a dedicated system user

Do not run the bot as root or as your personal user:

```bash
sudo adduser --system --group --home /opt/twitch-bot --shell /usr/sbin/nologin twitchbot
```

## 2. Get the code onto the server

```bash
sudo -u twitchbot git clone https://github.com/d43m0n4rch7/twitch-bot.git /opt/twitch-bot
cd /opt/twitch-bot
```

If the repo is private, generate a deploy key (read-only) for `twitchbot`
instead of using a personal SSH key:

```bash
sudo -u twitchbot mkdir -p /opt/twitch-bot/.ssh
sudo -u twitchbot ssh-keygen -t ed25519 -f /opt/twitch-bot/.ssh/id_ed25519 -N ""
sudo -u twitchbot cat /opt/twitch-bot/.ssh/id_ed25519.pub
```

Add the printed public key as a **read-only deploy key** in the repo
Settings → Deploy keys.

## 3. Install uv and dependencies

```bash
sudo -u twitchbot -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u twitchbot -H bash -c 'cd /opt/twitch-bot && ~/.local/bin/uv sync --no-dev --frozen'
```

This creates `/opt/twitch-bot/.venv`. The deploy workflow calls `uv` directly;
`just` is optional for manual work on the server.

## 4. Create the production `.env`

```bash
sudo -u twitchbot cp /opt/twitch-bot/.env.example /opt/twitch-bot/.env
sudo -u twitchbot nano /opt/twitch-bot/.env
sudo chmod 600 /opt/twitch-bot/.env
sudo chown twitchbot:twitchbot /opt/twitch-bot/.env
```

Fill in `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `TWITCH_BOT_ID`,
`TWITCH_OWNER_ID`, `DATABASE_URL`, `EVENTSUB_SECRET`, and `OAUTH_DOMAIN`
(the public HTTPS domain from step 5, e.g. `https://oauth.example.com`).

In the Twitch Developer Console, set the app's OAuth Redirect URL to
`https://oauth.example.com/oauth/callback`.

## 5. Point Caddy at the bot

The bot's OAuth/EventSub adapter listens on `127.0.0.1:4343` and is never
exposed directly — Caddy terminates HTTPS and reverse-proxies to it.

Copy the provided config and point your DNS `A`/`AAAA` record for the
subdomain at this server first:

```bash
sudo cp /opt/twitch-bot/deploy/Caddyfile /etc/caddy/twitch-bot.caddy
sudo nano /etc/caddy/twitch-bot.caddy   # replace oauth.example.com with your real subdomain
```

Import it from the main Caddyfile (`/etc/caddy/Caddyfile`):

```
import /etc/caddy/twitch-bot.caddy
```

Or paste its contents into the main Caddyfile if you do not use `import`.
Then reload:

```bash
sudo systemctl reload caddy
```

## 6. Install the systemd service

The unit runs as **`User=twitchbot`** / **`Group=twitchbot`** (see
`deploy/twitch-bot.service`).

```bash
sudo cp /opt/twitch-bot/deploy/twitch-bot.service /etc/systemd/system/twitch-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now twitch-bot.service
sudo systemctl status twitch-bot.service
```

## 7. Authorize the bot, owner, and public channels

The systemd service and a manual `--scopes-only` run both bind port 4343,
so stop the service first:

```bash
sudo systemctl stop twitch-bot.service
sudo -u twitchbot /opt/twitch-bot/.venv/bin/python -m twitch_bot.main --scopes-only
```

This prints three links (BOT / OWNER / PUBLIC) built from `OAUTH_DOMAIN`.
With Caddy already proxying that domain, open each link in a browser and
complete Twitch's authorization screen — log in as the bot account for the
BOT link, then as the channel owner for the OWNER link, then as any other
channel for PUBLIC. Each authorization is saved to PostgreSQL immediately.

Stop the manual process (Ctrl+C) once done, then start the service:

```bash
sudo systemctl start twitch-bot.service
```

It loads the persisted tokens and all components on startup. Re-run this
step any time you need to authorize an additional public channel.

## 8. Allow `twitchbot` to restart the service without a password

The GitHub Actions workflow connects as **`twitchbot`** and must be able to
restart the unit without an interactive password. Only restart is required:

```bash
echo 'twitchbot ALL=(root) NOPASSWD: /usr/bin/systemctl restart twitch-bot.service' | sudo tee /etc/sudoers.d/twitch-bot
sudo chmod 440 /etc/sudoers.d/twitch-bot
sudo visudo -cf /etc/sudoers.d/twitch-bot
```

If `systemctl` is not at `/usr/bin/systemctl` on your host, use the path from
`which systemctl`.

## 9. Enable SSH login for `twitchbot` (deploy key)

GitHub Actions needs a login-capable shell for `twitchbot`:

```bash
sudo usermod -s /bin/bash twitchbot
sudo mkdir -p /opt/twitch-bot/.ssh
sudo chown twitchbot:twitchbot /opt/twitch-bot/.ssh
sudo chmod 700 /opt/twitch-bot/.ssh
```

Generate a dedicated deploy keypair **on your own machine** (not the server):

```bash
ssh-keygen -t ed25519 -f ./gh_deploy_key -N ""
```

Install the public key on the server:

```bash
cat gh_deploy_key.pub | sudo tee -a /opt/twitch-bot/.ssh/authorized_keys
sudo chmod 600 /opt/twitch-bot/.ssh/authorized_keys
sudo chown twitchbot:twitchbot /opt/twitch-bot/.ssh/authorized_keys
```

Keep the private key (`gh_deploy_key`) for `DEPLOY_SSH_KEY` below. Remove it
from your machine once it is stored in GitHub Secrets.

## 10. Add GitHub secrets

Repo Settings → Secrets and variables → Actions:

| Secret            | Value                                        |
|-------------------|----------------------------------------------|
| `DEPLOY_HOST`     | VPS IP or hostname                           |
| `DEPLOY_USER`     | `twitchbot`                                  |
| `DEPLOY_PORT`     | SSH port (usually `22`)                      |
| `DEPLOY_SSH_KEY`  | contents of the private key (`gh_deploy_key`)|
| `DEPLOY_PATH`     | `/opt/twitch-bot`                            |

## 11. Test it

Push a commit to `main`, then watch the Actions tab. The workflow connects as
`twitchbot`, resets the repo to `origin/main`, runs
`uv sync --no-dev --frozen`, and restarts `twitch-bot.service`.

## Notes

- `OAUTH_DOMAIN` must point at this server and go through Caddy over HTTPS —
  Twitch requires HTTPS for OAuth and EventSub callbacks in production.
- Alembic migrations are applied automatically on every bot start
  (`run_migrations`). You can also run `uv run alembic upgrade head` as
  `twitchbot` manually.
- Rotate `DEPLOY_SSH_KEY` and `EVENTSUB_SECRET` if either is ever exposed.
