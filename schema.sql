-- ZicoWorldFast bot uchun Supabase jadval sxemasi
-- Buni Supabase loyihangizda: SQL Editor -> New Query -> shu kodni joylashtiring -> Run

create table if not exists users (
    telegram_id bigint primary key,
    username text,
    first_seen timestamptz default now()
);

create table if not exists settings (
    id int primary key,
    maintenance boolean default false
);

insert into settings (id, maintenance)
values (1, false)
on conflict (id) do nothing;

create table if not exists tournaments (
    id serial primary key,
    size int not null,
    status text not null default 'registration', -- registration | ongoing | stopped
    deadline timestamptz not null,
    created_at timestamptz default now()
);

create table if not exists participants (
    id serial primary key,
    tournament_id int references tournaments(id) on delete cascade,
    telegram_id bigint not null,
    username text not null,
    registered_at timestamptz default now(),
    unique (tournament_id, telegram_id)
);

create table if not exists matches (
    id serial primary key,
    tournament_id int references tournaments(id) on delete cascade,
    player1_id bigint not null,
    player1_username text not null,
    player2_id bigint,
    player2_username text,
    created_at timestamptz default now()
);

create index if not exists idx_participants_tournament on participants(tournament_id);
create index if not exists idx_matches_tournament on matches(tournament_id);
