# de1-docker-compose-Postgres-SQL-Terraform-workshop

Docker and PostgreSQL: Data Engineering Workshop

> **Note:** This workshop covers Docker and PostgreSQL. For Terraform/GCP setup, see the [Terraform GCP Setup](#terraform-gcp-setup) section below.

In this workshop, we will explore Docker fundamentals and data engineering workflows using Docker containers.

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

## Docker Compose

docker-compose allows us to launch multiple containers using a single configuration file, so that we don't have to run multiple complex docker run commands separately.

Docker compose makes use of YAML files. Here's the docker-compose.yaml file for running the Postgres and pgAdmin containers:

```yaml
services:
  pgdatabase:
    image: postgres:18
    environment:
      - POSTGRES_USER=root
      - POSTGRES_PASSWORD=root
      - POSTGRES_DB=ny_taxi
    volumes:
      - "ny_taxi_postgres_data:/var/lib/postgresql:rw"
    ports:
      - "5432:5432"
  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=root
    volumes:
      - "pgadmin_data:/var/lib/pgadmin"
    ports:
      - "8085:80"

volumes:
  ny_taxi_postgres_data:
  pgadmin_data:
```

We don't have to specify a network because docker-compose takes care of it: every single container (or "service", as the file states) will run within the same network and will be able to find each other according to their names (pgdatabase and pgadmin in this example).
All other details from the docker run commands (environment variables, volumes and ports) are mentioned accordingly in the file following YAML syntax.
Start Services with Docker Compose

We can now run Docker compose by running the following command from the same directory where docker-compose.yaml is found. Make sure that all previous containers aren't running anymore:

```bash
docker-compose up
```

Note: this command assumes that the ny_taxi_postgres_data used for mounting the volume is in the same directory as docker-compose.yaml.

Since the settings for pgAdmin were stored within the container and we have killed the previous one, you will have to re-create the connection by following the steps in the pgAdmin section.

You will have to press Ctrl+C in order to shut down the containers. The proper way of shutting them down is with this command:

```bash
docker-compose down
```

And if you want to run the containers again in the background rather than in the foreground (thus freeing up your terminal), you can run them in detached mode:

```bash
docker-compose up -d
```

Other useful commands:

```bash
# View logs
docker-compose logs

# Stop and remove volumes
docker-compose down -v
```

Benefits of Docker Compose:

- Single command to start all services
- Automatic network creation
- Easy configuration management
- Declarative infrastructure

If you want to re-run the dockerized ingest script when you run Postgres and pgAdmin with docker-compose, you will have to find the name of the virtual network that Docker compose created for the containers. You can use the command docker network ls to find it and then change the docker run command for the dockerized script to include the network name.

```bash
# check the network link:
docker network ls 

# it's pipeline_default
# now run the script:
docker run -it \
  --network=pipeline_default \
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

## Terraform GCP Setup

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
```
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

#### Setup Steps:

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

```
terraform/
├── provider.tf            # Google provider configuration
├── variables.tf           # Variable definitions
└── terraform.tfvars.example  # Template (copy to terraform.tfvars)
```
