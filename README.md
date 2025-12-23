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

## Using pgAdmin - Database Management Tool

pgcli is a handy tool but it's cumbersome to use for complex queries and database management. pgAdmin is a web-based tool that makes it more convenient to access and manage our databases.

It's possible to run pgAdmin as a container along with the Postgres container, but both containers will have to be in the same virtual network so that they can find each other.

### Run pgAdmin Container

```bash
docker run -it \
  -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" \
  -e PGADMIN_DEFAULT_PASSWORD="root" \
  -v pgadmin_data:/var/lib/pgadmin \
  -p 8085:80 \
  dpage/pgadmin4
```

The -v pgadmin_data:/var/lib/pgadmin volume mapping saves pgAdmin settings (server connections, preferences) so you don't have to reconfigure it every time you restart the container.

The container needs 2 environment variables: a login email and a password. We use admin@admin.com and root in this example.

pgAdmin is a web app and its default port is 80; we map it to 8085 in our localhost to avoid any possible conflicts.

The actual image name is dpage/pgadmin4.

Note: This won't work yet because pgAdmin can't see the PostgreSQL container. They need to be on the same Docker network!

### Docker Networks

Let's create a virtual Docker network called pg-network:

```bash
docker network create pg-network
```

You can remove the network later with the command docker network rm pg-network. You can look at the existing networks with ```docker network ls```.

Stop both containers and re-run them with the network configuration:

```bash
# Run PostgreSQL on the network
docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v ny_taxi_postgres_data:/var/lib/postgresql \
  -p 5432:5432 \
  --network=pg-network \
  --name pgdatabase \
  postgres:18

# In another terminal, run pgAdmin on the same network
docker run -it \
  -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" \
  -e PGADMIN_DEFAULT_PASSWORD="root" \
  -v pgadmin_data:/var/lib/pgadmin \
  -p 8085:80 \
  --network=pg-network \
  --name pgadmin \
  dpage/pgadmin4
```

Just like with the Postgres container, we specify a network and a name for pgAdmin.

The container names (pgdatabase and pgadmin) allow the containers to find each other within the network.

### Connect pgAdmin to PostgreSQL

You should now be able to load pgAdmin on a web browser by browsing to

```http://localhost:8085```. 

Use the same email and password you used for running the container to log in.

Open browser and go to ```http://localhost:8085```

Login with email: ```admin@admin.com```, password: root

Right-click "Servers" → Register → Server

Configure:

- General tab: Name: Local Docker
- Connection tab:
- Host: pgdatabase (the container name)
- Port: 5432
- Username: root
- Password: root
- Save

Now you can explore the database using the pgAdmin interface!

## Dockerizing the Ingestion Script

Let's modify the Dockerfile we created before to include our ingest_data.py script:

```bash
# Start with slim Python 3.13 image for smaller size
FROM python:3.13.11-slim

# Copy uv binary from official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Set working directory inside container
WORKDIR /app

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first (better caching)
COPY "pyproject.toml" "uv.lock" ".python-version" ./
# Install all dependencies (pandas, sqlalchemy, psycopg2)
RUN uv sync --locked

# Copy ingestion script
COPY ingest_data.py ingest_data.py 

# Set entry point to run the ingestion script
ENTRYPOINT [ "python", "ingest_data.py" ]
```

Explanation:

```uv sync --locked``` installs exact versions from uv.lock for reproducibility

Dependencies (pandas, sqlalchemy, psycopg2) are already in pyproject.toml

Multi-stage build pattern copies uv from official image

Copying dependency files before code improves Docker layer caching

### Build the Docker Image

```bash
docker build -t taxi_ingest:v001 .
```

### Run the Containerized Ingestion

You can drop the table in pgAdmin beforehand if you want, but the script will automatically replace the pre-existing table.

```bash
docker run -it \
  --network=pg-network \
  taxi_ingest:v001 \
    --pg-user=root \
    --pg-pass=root \
    --pg-host=pgdatabase \
    --pg-port=5432 \
    --pg-db=ny_taxi \
    --target-table=yellow_taxi_trips_2021_2 \
    --year=2021 \
    --month=2 \
    --chunksize=100000
```

Important notes:

- We need to provide the network for Docker to find the Postgres container. It goes before the name of the image.
- Since Postgres is running on a separate container, the host argument will have to point to the container name of Postgres (pgdatabase).
- You can drop the table in pgAdmin beforehand if you want, but the script will automatically replace the pre-existing table.
