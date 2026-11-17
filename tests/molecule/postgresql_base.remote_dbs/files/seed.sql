-- The postgres image runs this once, when it initializes the database. Init
-- scripts connect to POSTGRES_DB (defaults to POSTGRES_USER, "root").
\connect postgres

-- For the role to drop
CREATE ROLE repeaters_fdw_user LOGIN;

-- For the devreadonly ALL_IN_SCHEMA grant
CREATE TABLE molecule_privs_check (id int);
