# de1-docker-workshop

Docker and PostgreSQL: Data Engineering Workshop

In this workshop, we will explore Docker fundamentals and data engineering workflows using Docker containers. This workshop is an update for Module 1 of the Data Engineering Zoomcamp.

Data Engineering is the design and development of systems for collecting, storing and analyzing data at scale.

We will cover:

- Introduction to Docker and containerization
- Running PostgreSQL in a Docker container
- Data ingestion into PostgreSQL
- Working with pgAdmin for database management
- Docker networking and port mapping
- Docker Compose for multi-container applications
- Creating a data ingestion pipeline
- SQL refresher with real-world data
- Best practices for containerized data engineering workflows

## Run Postgres in Docker container

We use bind mount:

First create the directory, then map it:

```bash
mkdir ny_taxi_postgres_data

docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v $(pwd)/ny_taxi_postgres_data:/var/lib/postgresql \
  -p 5432:5432 \
  postgres:18
```

When you create the directory first, it's owned by your user. If you let Docker create it, it will be owned by the Docker/root user, which can cause permission issues on Linux. On Windows and macOS with Docker Desktop, this is handled automatically.

Named volume vs Bind mount:

Named volume (name:/path): Managed by Docker, easier

Bind mount (/host/path:/container/path): Direct mapping to host filesystem, more control

Once the container is running, we can log into our database with pgcli.

Install pgcli:

```bash
uv add --dev pgcli
```

The --dev flag marks this as a development dependency (not needed in production). It will be added to the [dependency-groups] section of pyproject.toml instead of the main dependencies section.

Now use it to connect to Postgres:

```bash
uv run pgcli -h localhost -p 5432 -u root -d ny_taxi
```

uv run executes a command in the context of the virtual environment

- -h is the host. Since we're running locally we can use localhost.
- -p is the port.
- -u is the username.
- -d is the database name.
The password is not provided; it will be requested after running the command.
When prompted, enter the password: root

Useful SQL commands:

```bash
-- List tables
\dt

-- Create a test table
CREATE TABLE test (id INTEGER, name VARCHAR(50));

-- Insert data
INSERT INTO test VALUES (1, 'Hello Docker');

-- Query data
SELECT * FROM test;

-- Exit
\q
```

## Ingest NY Trips Database data to our Postgres instance

We use parameterised ingest_data.py script which reads data in chunks (100,000 rows at a time) to handle large files efficiently without running out of memory.

Make sure PostgreSQL is running, then execute the ingestion script:

```bash
uv run python ingest_data.py \
  --pg-user=root \
  --pg-pass=root \
  --pg-host=localhost \
  --pg-port=5432 \
  --pg-db=ny_taxi \
  --target-table=yellow_taxi_trips \
  --year=2021 \
  --month=1 \
  --chunksize=100000
```

We can verify data after injection.

Connect with pgcli and query the data:

```bash
uv run pgcli -h localhost -p 5432 -u root -d ny_taxi
-- Count records (should return 1,369,765 rows)
SELECT COUNT(*) FROM yellow_taxi_trips;

-- View sample data
SELECT * FROM yellow_taxi_trips LIMIT 10;

-- Basic analytics
SELECT 
    DATE(tpep_pickup_datetime) AS pickup_date,
    COUNT(*) AS trips_count,
    AVG(total_amount) AS avg_amount
FROM yellow_taxi_trips
GROUP BY DATE(tpep_pickup_datetime)
ORDER BY pickup_date;
```
