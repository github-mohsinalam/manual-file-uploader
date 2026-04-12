-- Enable the pgcrypto extension which gives us gen_random_uuid()
-- This must run before any table that uses UUID as a default value
-- Extensions in PostgreSQL are like libraries in Python -- 
-- they add extra functionality that is not in the core engine

CREATE EXTENSION IF NOT EXISTS "pgcrypto";