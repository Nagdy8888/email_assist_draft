-- Drop the email_assistant schema and all objects in it.
-- Run this first when you want a clean slate, then run 001_email_assistant_tables.sql.
-- WARNING: This deletes all data in the schema.

DROP SCHEMA IF EXISTS email_assistant CASCADE;
