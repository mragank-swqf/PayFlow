-- Runs once on first Postgres volume init.
-- POSTGRES_DB already creates "payflow"; this adds the test DB for Day 12+.
CREATE DATABASE payflow_test;
