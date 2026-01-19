#!/usr/bin/env python3
"""
Simple loader: push parquet and CSV files into Postgres using Docker Compose.
Run with: docker-compose run loader

The loader connects to PostgreSQL using the Docker service name 'db'.
"""

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text

# PostgreSQL connection (service name 'db' from docker-compose)
ENGINE = create_engine("postgresql+psycopg2://postgres:postgres@db:5432/ny_taxi")

# Files to ingest
FILES = [
    {"path": "data/green_tripdata_2025-11.parquet", "table": "green_trips"},
    {"path": "data/taxi_zone_lookup.csv", "table": "taxi_zones"},
]

print(f"PostgreSQL: db:5432/ny_taxi")
print("-" * 50)

for file_info in FILES:
    filepath = file_info["path"]
    table_name = file_info["table"]
    
    print(f"Loading: {filepath}")
    
    # Load file based on extension
    if filepath.endswith(".parquet"):
        df = pd.read_parquet(filepath)
    elif filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        print(f"  Skipping unknown file type: {filepath}")
        continue
    
    print(f"  Read {len(df):,} rows from {filepath.split('/')[-1]}")
    
    # Push to PostgreSQL
    df.to_sql(table_name, ENGINE, if_exists="replace", index=False)
    print(f"  Loaded into table '{table_name}'")
    
    # Verify
    with ENGINE.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        print(f"  Success! Table has {count:,} rows")
    
    print("-" * 50)

print("All files loaded successfully!")
