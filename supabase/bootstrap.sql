-- Run once in the Supabase SQL editor before applying Django migrations.
-- FlatHunter AI uses GeoDjango PointField columns and spatial queries.
create extension if not exists postgis;
