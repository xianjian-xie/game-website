create table game (
    name varchar(255) PRIMARY KEY,
    picture bytea,
    video varchar(255),
    popularity int,
    rating float,
    description varchar(255),
    platform varchar(255)
)

create table tag (
    name varchar(255) PRIMARY KEY
)

create table game_tag (
    game varchar(255),
    tag varchar(255),
    count int,
    CONSTRAINT fk_game FOREIGN KEY(game) REFERENCES game(name),
    CONSTRAINT fk_tag FOREIGN KEY(tag) REFERENCES tag(name),
    PRIMARY KEY(game, tag)
)

create table reviewer (
    id serial PRIMARY KEY,
    oauth_id varchar(255)
)

create table review (
    id serial PRIMARY KEY,
    reviewer int,
    game varchar(255),
    timestamp TIMESTAMP DEFAULT NOW(),
    title varchar(255),
    content varchar(2550),
    rating int,
    CONSTRAINT fk_reviewer FOREIGN KEY(reviewer) REFERENCES reviewer(id),
    CONSTRAINT fk_game FOREIGN KEY(game) REFERENCES game(name)
)





drop table gift_idea;
drop table person;
drop table images;

create table person (
  person_id SERIAL PRIMARY KEY,
  description text default '',
  name varchar(255) NOT NULL
);

create table gift_idea (
  gift_idea_id SERIAL PRIMARY KEY,
  person_id int references person,
  product varchar(255) NOT NULL,
  external_link varchar(255)
);

-- A table to hold images.
create table images (
  image_id SERIAL PRIMARY KEY,
  filename text,
  data bytea
);

insert into person (name) values ('Yang He');
insert into person (name) values ('Daniel Kluver');

-- I know a weird number of people named laura
insert into person (name) values ('Laura');
insert into person (name) values ('Laura (house)');
insert into person (name) values ('Laura (family)');
