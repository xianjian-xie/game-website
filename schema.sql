drop table game;
drop table tag;
drop table game_tag;
drop table reviewer;
drop table review;

create table game (
    name varchar(255) PRIMARY KEY,
    picture bytea,
    video varchar(255),
    popularity int,
    rating float,
    description varchar(255),
    platform varchar(255)
);

create table tag (
    name varchar(255) PRIMARY KEY
);

create table game_tag (
    game varchar(255),
    tag varchar(255),
    count int,
    CONSTRAINT fk_game FOREIGN KEY(game) REFERENCES game(name),
    CONSTRAINT fk_tag FOREIGN KEY(tag) REFERENCES tag(name),
    PRIMARY KEY(game, tag)
);

create table reviewer (
    id serial PRIMARY KEY,
    oauth_id varchar(255)
);

create table review (
    id serial PRIMARY KEY,
    reviewer int,
    game varchar(255),
    timestamp TIMESTAMP DEFAULT NOW(),
    title varchar(255),
    content text,
    rating int,
    CONSTRAINT fk_reviewer FOREIGN KEY(reviewer) REFERENCES reviewer(id),
    CONSTRAINT fk_game FOREIGN KEY(game) REFERENCES game(name)
);