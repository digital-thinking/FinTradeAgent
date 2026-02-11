-- Development Database initialization script
-- This script is run automatically when the development database starts

-- Create additional development users
CREATE USER fintradeagent_readonly WITH PASSWORD 'readonly_dev_123';
CREATE USER fintradeagent_test WITH PASSWORD 'test_dev_123';

-- Grant appropriate permissions
GRANT CONNECT ON DATABASE fintradeagent_dev TO fintradeagent_readonly;
GRANT CONNECT ON DATABASE fintradeagent_dev TO fintradeagent_test;

-- Create development schema
\c fintradeagent_dev;

-- Grant schema permissions
GRANT USAGE ON SCHEMA public TO fintradeagent_readonly, fintradeagent_test;

-- Enable extensions that might be useful for development
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create development-specific tables or views if needed
-- (This will be expanded as the project evolves)

-- Set up logging for development
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 0;
SELECT pg_reload_conf();

-- Create a development admin user with all privileges
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dev_admin') THEN
      CREATE ROLE dev_admin LOGIN PASSWORD 'dev_admin_123';
      GRANT ALL PRIVILEGES ON DATABASE fintradeagent_dev TO dev_admin;
      ALTER USER dev_admin CREATEDB CREATEROLE;
   END IF;
END
$$;