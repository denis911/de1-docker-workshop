# de1-Docker-PostgreSQL-GCP-Terraform-workshop

Docker, PostgreSQL & Terraform: Data Engineering Workshop

In this workshop, we explore Docker fundamentals, PostgreSQL, and cloud infrastructure with Terraform on Google Cloud Platform.

Data Engineering is the design and development of systems for collecting, storing and analyzing data at scale.

## Project Structure

```bash
├── data/                   # Data files (parquet, CSV) - not commited to Github
│   ├── green_tripdata_2025-11.parquet
│   └── taxi_zone_lookup.csv
├── terraform/              # GCP Terraform configuration
├── pipeline/               # Pipeline scripts
├── test/                   # Test files
├── ingest_pipeline.py      # Data ingestion pipeline
├── ingest_data.py          # Data ingestion script
├── docker-compose.yaml     # Docker services (PostgreSQL, pgAdmin, loader)
├── Dockerfile-test         # For debugging/testing
└── README.md
```

## Workshop Contents

1. **Docker Compose** - PostgreSQL, pgAdmin, loader (recommended)
2. **Load Data** - Parquet files into PostgreSQL
3. **Docker Testing** - Interactive container for debugging
4. **Terraform on GCP** - Cloud infrastructure with Google Cloud Platform

--- DETAILED CONTENTS ---

## 1. Docker Basics

### What You'll Learn

- Running PostgreSQL in a Docker container
- Data ingestion into PostgreSQL
- Working with pgAdmin for database management
- Docker networking and port mapping
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
uv run pgcli -h localhost -p 5433 -u postgres -d ny_taxi
```

uv run executes a command in the context of the virtual environment

- -h is the host. Since we're running locally we can use localhost.
- -p is the port.
- -u is the username.
- -d is the database name.
The password is not provided; it will be requested after running the command.
When prompted, enter the password: `postgres`

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

Make sure PostgreSQL is running (via Docker Compose), then execute the ingestion script:

```bash
uv run python ingest_data.py \
  --pg-user=postgres \
  --pg-pass=postgres \
  --pg-host=localhost \
  --pg-port=5433 \
  --pg-db=ny_taxi \
  --target-table=yellow_taxi_trips \
  --year=2021 \
  --month=1 \
  --chunksize=100000
```

We can verify data after injection.

Connect with pgcli and query the data:

```bash
uv run pgcli -h localhost -p 5433 -u postgres -d ny_taxi
```

Then run:

```sql
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

## 2. Docker Testing (Interactive Debugging)

A special Dockerfile (`Dockerfile-test`) is provided for testing and debugging Python/pip inside containers.

### Build and Run

**Windows (PowerShell):**

```powershell
# Build the image
docker build -f Dockerfile-test -t test-image .

# Run interactively (auto-remove on exit)
docker run -it --rm test-image
```

### Inside the Container

Once inside the bash shell, you can:

```bash
# Check Python version
python --version

# List installed packages
pip list

# Run Python scripts
python pipeline.py

# Use uv to run commands
uv run python pipeline.py
```

### Exit the Container

Type `exit` or press `Ctrl+D` - the container will be automatically removed.

### Quick One-Liner

```powershell
docker build -f Dockerfile-test -t test-image . && docker run -it --rm test-image
```

## 3. Docker Compose

Docker Compose allows us to launch multiple containers using a single configuration file, so that we don't have to run multiple complex `docker run` commands separately.

Here's the `docker-compose.yaml` file for running Postgres and pgAdmin containers:

```yaml
services:
  db:
    container_name: postgres
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: 'postgres'
      POSTGRES_PASSWORD: 'postgres'
      POSTGRES_DB: 'ny_taxi'
    ports:
      - '5433:5432'
    volumes:
      - vol-pgdata:/var/lib/postgresql/data

  pgadmin:
    container_name: pgadmin
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: "pgadmin@pgadmin.com"
      PGADMIN_DEFAULT_PASSWORD: "pgadmin"
    ports:
      - "8080:80"
    volumes:
      - vol-pgadmin_data:/var/lib/pgadmin

volumes:
  vol-pgdata:
    name: vol-pgdata
  vol-pgadmin_data:
    name: vol-pgadmin_data
```

### Key Changes

- **PostgreSQL**: Uses `postgres:17-alpine` (lighter image)
- **Port**: Maps to `5433` (instead of `5432`) to avoid conflicts
- **Credentials**: Uses `postgres`/`postgres` for both DB and pgAdmin
- **Volume names**: Explicitly named for clarity

### Start Services

We don't have to specify a network because Docker Compose takes care of it automatically. All containers run within the same network and can find each other by service name.

Run Docker Compose from the directory where `docker-compose.yaml` is located:

```bash
# Start services in foreground
docker-compose up

# Or start in background (detached mode)
docker-compose up -d
```

### Access the Services

- **PostgreSQL**: `localhost:5433` (user: `postgres`, password: `postgres`, db: `ny_taxi`)
- **pgAdmin**: [http://localhost:8080](http://localhost:8080) (email: `pgadmin@pgadmin.com`, password: `pgadmin`)

### Stop Services

Press `Ctrl+C` to stop foreground services, or run:

```bash
# Stop and remove containers
docker-compose down

# Stop and remove volumes (data will be lost)
docker-compose down -v
```

### Useful Commands

```bash
# View logs
docker-compose logs

# View logs for specific service
docker-compose logs db
docker-compose logs pgadmin

# Restart a service
docker-compose restart db

# Check status
docker-compose ps
```

### Connect to PostgreSQL

**Using pgcli:**

```bash
uv run pgcli -h localhost -p 5433 -u postgres -d ny_taxi
```

Password: `postgres`

**Using psql:**

```bash
docker exec -it postgres psql -U postgres -d ny_taxi
```

### Configure pgAdmin to Connect to PostgreSQL

1. Open browser and go to [http://localhost:8080](http://localhost:8080)
2. Login with email: `pgadmin@pgadmin.com`, password: `pgadmin`
3. Right-click **Servers** → **Register** → **Server**
4. Configure the connection:
   - **General** tab:
     - Name: `Local Docker Postgres`
   - **Connection** tab:
     - Host name/address: `db` (Docker Compose service name)
     - Port: `5432` (internal PostgreSQL port)
     - Username: `postgres`
     - Password: `postgres`
5. Click **Save**

## 5. Load Parquet Data into PostgreSQL

A simple loader script (`ingest_pipeline.py`) pushes parquet and CSV files from the `data/` directory into PostgreSQL.

### Data Directory

All data files are stored in the `data/` directory:

- `green_tripdata_2025-11.parquet` - Green taxi trip data
- `taxi_zone_lookup.csv` - Taxi zone lookup table

### Run the Loader

The `loader` service is defined in `docker-compose.yaml`. It:

- Mounts the current directory so it can access `data/` folder
- Waits for PostgreSQL to be healthy before running
- Installs dependencies and runs the ingestion script

**Start the loader:**

```bash
docker-compose run loader
```

This will:

1. Start PostgreSQL if not running (waits for it to be healthy)
2. Run the loader which reads all files from `data/` directory
3. Load data into PostgreSQL:
   - `green_tripdata_2025-11.parquet` → `green_trips` table
   - `taxi_zone_lookup.csv` → `taxi_zones` table

**Or run everything together:**

```bash
docker-compose up -d db pgadmin  # Start DB and pgAdmin
docker-compose run loader         # Run loader to ingest data
```

### How It Works

```python
# ingest_pipeline.py - Loads parquet and CSV files into PostgreSQL
FILES = [
    {"path": "data/green_tripdata_2025-11.parquet", "table": "green_trips"},
    {"path": "data/taxi_zone_lookup.csv", "table": "taxi_zones"},
]

for file_info in FILES:
    df = pd.read_parquet(file_info["path"])  # or pd.read_csv()
    df.to_sql(file_info["table"], ENGINE, if_exists="replace", index=False)
```

### Verify the Data

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d ny_taxi

# Query the loaded tables
SELECT COUNT(*) FROM green_trips;
SELECT COUNT(*) FROM taxi_zones;

# Join example
SELECT * 
FROM green_trips t
JOIN taxi_zones z ON t.pulocationid = z.locationid
LIMIT 5;
```

### Using pgAdmin

1. Go to [http://localhost:8080](http://localhost:8080)
2. Login with `pgadmin@pgadmin.com` / `pgadmin`
3. You should see both tables under `Tables`:
   - `green_trips` - Green taxi trip data
   - `taxi_zones` - Taxi zone lookup table

## 4. Terraform on GCP

### Creating a GCP Service Account for Terraform

To provision GCP resources (like GCS buckets and BigQuery datasets) with Terraform, you need to create a dedicated service account.

#### Step 1: Create the Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Click **+ CREATE SERVICE ACCOUNT**
4. Fill in:
   - **Service account name**: `terraform`
   - **Service account description**: `Service account for Terraform infrastructure management`
5. Click **CREATE AND CONTINUE**
6. Grant the following roles:
   - **Storage Admin** (for GCS buckets)
   - **BigQuery Admin** (for BigQuery datasets)
   - **Editor** (or specific roles for the resources you need)
7. Click **DONE**

#### Step 2: Download the Service Account JSON Key

**Yes, you must download the JSON key file** - GCP Console cannot automatically pick up credentials from the cloud for Terraform running on your local workstation.

1. In the Service Accounts list, find your `terraform` service account
2. Click on the **Actions** (three dots) menu → **Manage keys**
3. Click **ADD KEY** → **Create new key**
4. Select **JSON** key type
5. Click **CREATE** - the JSON file will download to your computer
6. Save it securely (e.g., `~/.gcp/terraform-service-account.json`)

#### Step 3: Configure Terraform Authentication

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your JSON key file:

**Windows (PowerShell) - Session only (will reset after restart):**

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\yourusername\.gcp\terraform-service-account.json"
```

**Windows (CMD) - Session only (will reset after restart):**

```cmd
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\yourusername\.gcp\terraform-service-account.json
```

**Linux/macOS (Bash) - Session only (will reset after restart):**

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/yourusername/.gcp/terraform-service-account.json"
```

#### Making Environment Variables Persistent on Windows

The commands above only set the variable for the current terminal session. To make it persist across restarts:

**Option 1: User Environment Variable (Recommended)**

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** → **Environment Variables**
3. Under **User variables**, click **New**
4. Variable name: `GOOGLE_APPLICATION_CREDENTIALS`
5. Variable value: `C:\Users\yourusername\.gcp\terraform-service-account.json`
6. Click **OK** on all dialogs

**Option 2: System Environment Variable**

1. Same as above, but click **New** under **System variables** instead
2. Requires admin privileges

**Option 3: Using PowerShell Profile (PowerShell only)**

```powershell
# Add to your PowerShell profile
Add-Content -Path $PROFILE -Value '$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\yourusername\.gcp\terraform-service-account.json"'
```

**Option 4: Using .env file in project**
Create a `.env` file in your Terraform project directory:

```bash
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\yourusername\.gcp\terraform-service-account.json
```

Then use a tool like [`tfenv`](https://github.com/tfutils/tfenv) or load it in your shell before running Terraform.

#### Step 4: Configure Terraform Provider

Create or update your `provider.tf`:

```hcl
provider "google" {
  project = "your-gcp-project-id"
  region  = "us-central1"
}

provider "google-beta" {
  project = "your-gcp-project-id"
  region  = "us-central1"
}
```

#### Step 5: Initialize and Use Terraform

```bash
terraform init
terraform plan
terraform apply
```

### Security Best Practices

- **Never commit the JSON key file to version control** - add it to `.gitignore`
- **Rotate keys periodically** - create new keys and revoke old ones
- **Use minimal permissions** - only grant the roles needed for your resources
- **Consider using Workload Identity** for production/GKE environments

### Alternative: gcloud Application Default Credentials

For development, you can also use your personal Google account:

```bash
gcloud auth application-default login
```

This will open a browser for authentication, but for Terraform automation, the service account approach is recommended.

### Terraform Configuration Files

The project includes Terraform configuration files in the `terraform/` directory:

- `provider.tf` - Google provider configuration
- `variables.tf` - Variable definitions for GCP project and region
- `terraform.tfvars.example` - Template for your project-specific values

#### Setup Steps

1. **Copy the example tfvars file:**

   ```bash
   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
   ```

2. **Edit `terraform.tfvars` and fill in your GCP project ID:**

   ```hcl
   gcp_project_id = "your-actual-project-id"
   gcp_region     = "us-central1"
   ```

3. **Initialize Terraform:**

   ```bash
   cd terraform
   terraform init
   ```

4. **Run Terraform commands:**

   ```bash
   terraform plan
   terraform apply
   ```

#### Security Note

- `terraform/terraform.tfvars` is in `.gitignore` and will NOT be committed
- Your JSON service account key is also protected by `.gitignore`
- Only `terraform.tfvars.example` is version controlled as a template

#### Project Structure

```bash
terraform/
├── provider.tf            # Google provider configuration
├── variables.tf           # Variable definitions
└── terraform.tfvars.example  # Template (copy to terraform.tfvars)
```
