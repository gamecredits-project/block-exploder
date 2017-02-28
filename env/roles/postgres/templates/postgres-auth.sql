CREATE DATABASE {{ postgres_db }};

CREATE USER {{ postgres_user }} WITH PASSWORD {{ postgres_pass }};

GRANT ALL PRIVILEGES ON DATABASE {{ postgres_db }} TO {{ postgres_user}};

ALTER USER {{ postgres_user }} CREATEDB;