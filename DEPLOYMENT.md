# Деплой

Настраивает бота на VPS за Caddy, как systemd-сервис, с автодеплоем через
GitHub Actions при каждом пуше в `main`.

Предполагается Ubuntu/Debian, root (или sudo) на VPS и уже установленный
Caddy (`sudo apt install caddy` или официальный репозиторий —
см. https://caddyserver.com/docs/install).

## 1. Создать отдельного системного пользователя

Не запускайте бота от root или от личного пользователя. Создайте
пользователя без login shell и без пароля:

```bash
sudo adduser --system --group --home /opt/twitch-bot --shell /usr/sbin/nologin twitchbot
```

## 2. Скачать код на сервер

```bash
sudo -u twitchbot git clone https://github.com/d43m0n4rch7/twitch-bot.git /opt/twitch-bot
cd /opt/twitch-bot
```

Если репозиторий приватный, сгенерируйте deploy key (только на чтение)
вместо личного SSH-ключа:

```bash
sudo -u twitchbot ssh-keygen -t ed25519 -f /opt/twitch-bot/.ssh/id_ed25519 -N ""
sudo -u twitchbot cat /opt/twitch-bot/.ssh/id_ed25519.pub
```

Добавьте выведенный публичный ключ как **read-only deploy key** в
Settings → Deploy keys репозитория.

## 3. Установить uv, Just и зависимости

```bash
sudo -u twitchbot -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo apt install just   # или: cargo install just / см. https://github.com/casey/just#installation
sudo -u twitchbot -H bash -c 'cd /opt/twitch-bot && ~/.local/bin/uv sync --no-dev --frozen'
```

Так появится `/opt/twitch-bot/.venv`. `just` нужен только если планируете
вручную гонять команды на сервере (`just run-twitch-scopes` и т.п.) —
workflow деплоя вызывает `uv` напрямую.

## 4. Создать production `.env`

```bash
sudo -u twitchbot cp /opt/twitch-bot/.env.example /opt/twitch-bot/.env
sudo -u twitchbot nano /opt/twitch-bot/.env
sudo chmod 600 /opt/twitch-bot/.env
```

Заполните `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `TWITCH_BOT_ID`,
`TWITCH_OWNER_ID`, `DATABASE_URL`, `EVENTSUB_SECRET` и `OAUTH_DOMAIN`
(публичный HTTPS-домен из шага 5, например `https://oauth.example.com`).

В Twitch Developer Console укажите OAuth Redirect URL приложения:
`https://oauth.example.com/oauth/callback`.

## 5. Направить Caddy на бота

OAuth/EventSub-адаптер бота слушает `127.0.0.1:4343` и наружу не торчит —
Caddy завершает HTTPS и reverse-proxy'ит на него. Так Twitch достучится
до бота без ngrok и подобных туннелей.

Скопируйте `deploy/Caddyfile` (или вставьте блок оттуда) и подставьте
свой поддомен:

```bash
sudo cp /opt/twitch-bot/deploy/Caddyfile /etc/caddy/twitch-bot.caddy
# отредактируйте oauth.example.com → ваш реальный поддомен
sudo nano /etc/caddy/twitch-bot.caddy
```

Импортируйте файл из основного Caddyfile:

```
import /etc/caddy/twitch-bot.caddy
```

или вставьте блок напрямую. Затем:

```bash
sudo systemctl reload caddy
```

Убедитесь, что DNS для поддомена указывает на этот VPS и что
`OAUTH_DOMAIN` в `.env` совпадает с ним (со схемой `https://`).

## 6. Поставить systemd unit

```bash
sudo cp /opt/twitch-bot/deploy/twitch-bot.service /etc/systemd/system/twitch-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now twitch-bot.service
```

Логи:

```bash
sudo journalctl -u twitch-bot.service -f
```

## 7. Авторизовать бота, владельца и публичные каналы

Запустите бота в режиме scopes-only (или откройте ссылки из логов при
обычном старте), откройте URL'ы BOT / OWNER / PUBLIC и пройдите
экран авторизации Twitch — для BOT зайдите под аккаунтом бота, для OWNER
под аккаунтом владельца канала, для PUBLIC под аккаунтом нужного
публичного канала. Каждая авторизация сразу сохраняется в PostgreSQL.

Повторяйте шаг PUBLIC, когда нужно авторизовать ещё один публичный канал.

## 8. Разрешить деплой-пользователю рестартовать сервис

GitHub Actions после `git pull` и `uv sync` перезапускает unit. Дайте
нужному пользователю право на это без пароля:

```bash
echo 'twitchbot ALL=(root) NOPASSWD: /usr/bin/systemctl restart twitch-bot.service, /usr/bin/systemctl is-active twitch-bot.service, /usr/bin/journalctl -u twitch-bot.service -n 50 --no-pager' | sudo tee /etc/sudoers.d/twitch-bot-deploy
sudo chmod 440 /etc/sudoers.d/twitch-bot-deploy
```

Сначала проверьте `which systemctl` и `which journalctl` и подставьте
реальные пути, если они отличаются от `/usr/bin/`.

## 9. Создать SSH-пользователя, к которому подключается GitHub Actions

Можно использовать того же пользователя, что владеет кодом (`twitchbot`),
если дать ему login shell, либо отдельного `deploy` с правом записи в
`/opt/twitch-bot` через общую группу. Проще всего — переиспользовать
`twitchbot`:

```bash
sudo usermod -s /bin/bash twitchbot
sudo mkdir -p /opt/twitch-bot/.ssh
sudo chown twitchbot:twitchbot /opt/twitch-bot/.ssh
sudo chmod 700 /opt/twitch-bot/.ssh
```

Сгенерируйте отдельную deploy-пару ключей **на своей машине** (не на
сервере):

```bash
ssh-keygen -t ed25519 -f ./gh_deploy_key -N ""
```

Добавьте публичный ключ на сервер:

```bash
cat gh_deploy_key.pub | sudo tee -a /opt/twitch-bot/.ssh/authorized_keys
sudo chmod 600 /opt/twitch-bot/.ssh/authorized_keys
sudo chown twitchbot:twitchbot /opt/twitch-bot/.ssh/authorized_keys
```

Приватный ключ (`gh_deploy_key`) уйдёт в `DEPLOY_SSH_KEY` ниже.
После сохранения в GitHub удалите его с локальной машины.

Если в шаге 8 использовали пользователя `deploy`, подправьте sudoers и
SSH под него и убедитесь, что у него есть запись в `/opt/twitch-bot`
(например, через общую группу).

## 10. Добавить секреты GitHub

Repo Settings → Secrets and variables → Actions:

| Secret           | Значение                                           |
|------------------|-----------------------------------------------------|
| `DEPLOY_HOST`    | IP или hostname VPS                                 |
| `DEPLOY_USER`    | `twitchbot` (или ваш `deploy`-пользователь)         |
| `DEPLOY_PORT`    | SSH-порт (обычно `22`)                              |
| `DEPLOY_SSH_KEY` | содержимое приватного ключа (`gh_deploy_key`)        |
| `DEPLOY_PATH`    | `/opt/twitch-bot`                                   |

## 11. Проверить

Запушьте коммит в `main` и смотрите вкладку Actions. Workflow прогонит
линтер, зайдёт по SSH, подтянет коммит, выполнит `uv sync`, перезапустит
сервис и упадёт с последними 50 строками логов, если сервис не поднялся.

## Заметки

- `OAUTH_DOMAIN` должен указывать на этот сервер и идти через Caddy по
  HTTPS — Twitch требует HTTPS для OAuth и EventSub callback'ов в проде.
- Схема БД применяется автоматически при каждом старте, отдельный шаг
  миграций в деплое не нужен.
- Ротируйте `DEPLOY_SSH_KEY` и `EVENTSUB_SECRET`, если они когда-либо
  утекут.
