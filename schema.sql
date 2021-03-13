drop table game_tag;
drop table review;
drop table game;
drop table tag;
drop table reviewer;


create table game (
    id SERIAL PRIMARY KEY,
    name varchar(255),
    picture varchar(255),
    video varchar(255),
    popularity int,
    rating float,
    shortdes text,
    longdes text,
    platform varchar(255),
    review_number int
);

create table tag (
    id SERIAL PRIMARY KEY,
    name varchar(255)
);

create table game_tag (
    game_id int,
    tag_id int,
    count int,
    CONSTRAINT fk_game FOREIGN KEY(game_id) REFERENCES game(id),
    CONSTRAINT fk_tag FOREIGN KEY(tag_id) REFERENCES tag(id),
    PRIMARY KEY(game_id, tag_id)
);

create table reviewer (
    id SERIAL PRIMARY KEY,
    oauth_id varchar(255),
    avatarlink varchar(255)
);

create table review (
    id SERIAL PRIMARY KEY,
    reviewer_id int,
    game_id int,
    timestamp TIMESTAMP DEFAULT NOW(),
    title varchar(255),
    content text,
    rating int,
    CONSTRAINT fk_reviewer FOREIGN KEY(reviewer_id) REFERENCES reviewer(id),
    CONSTRAINT fk_game FOREIGN KEY(game_id) REFERENCES game(id)
);

create table picture(
    id SERIAL PRIMARY KEY,
    picturelink varchar(255)
);

create table game_picture (
    game_id int,
    picture_id int,
    CONSTRAINT fk_game FOREIGN KEY(game_id) REFERENCES game(id),
    CONSTRAINT fk_tag FOREIGN KEY(picture_id) REFERENCES picture(id),
    PRIMARY KEY(game_id, picture_id)
);
