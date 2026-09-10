-- OAuth-токены Twitch. Сохраняются, чтобы бот мог перезапускаться
-- без повторной авторизации каждого канала.
create table if not exists twitch_tokens (
    user_id text primary key,
    access_token text not null,
    refresh_token text not null,
    scopes text[] not null default '{}',
    updated_at timestamptz not null default now()
);

-- Каналы, в которых бот был авторизован. "owner" — основной канал
-- (TWITCH_OWNER_ID), "bot" — сам аккаунт бота, "public" — любой
-- другой канал, авторизовавший бота через /oauth.
create table if not exists twitch_channels (
    user_id text primary key references twitch_tokens (user_id) on delete cascade,
    login text,
    display_name text,
    channel_type text not null check (channel_type in ('owner', 'bot', 'public')),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists twitch_channels_active_idx
    on twitch_channels (is_active)
    where is_active = true;
