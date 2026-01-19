#!/usr/bin/env python3
"""
Simple loader: push parquet file into Postgres using Docker Compose.
Run with: docker-compose run loader

The loader connects to PostgreSQL using the Docker service name 'db'.
"""

import pandas as pd
from sqlalchemy import create_engine

# PostgreSQL connection (service name 'db' from docker-compose)
ENGINE = create_engine("postgresql+psycopg2://postgres:postgres@db:5432/ny_taxi")

# Parquet file to ingest
PARQUET_FILE = "data/green_tripdata_2025-11.parquet"
TABLE_NAME = "green_trips"

print(f"Loading: {PARQUET_FILE}")
print(f"PostgreSQL: db:5432/ny_taxi")

# Load parquet
df = pd.read_parquet(PARQUET_FILE)
print(f"Read {len(df):,} rows from parquet")

# Push to PostgreSQL
df.to_sql(TABLE_NAME, ENGINE, if_exists="replace", index=False)
print(f"Loaded into table '{TABLE_NAME}'")

# Verify
# with ENGINE.connect() as conn:
#     result = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
#     count = result.fetchone()[0]
#     print(f"Success! Table has {count:,} rows")
