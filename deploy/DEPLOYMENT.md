# Living Classroom production deployment

This guide deploys the current Living Classroom application on Jeff's Linux server. Docker Compose runs PostgreSQL, database initialization, the Gunicorn web application, and continuous ingestion. Nginx runs directly on the server and proxies HTTP requests to the application on port 5000.

## 1. Prerequisites

Install and configure:

- Git
- Docker Engine
- Docker Compose (the `docker compose` command)
- Nginx

Confirm that each command is available:

```bash
git --version
docker --version
docker compose version
nginx -v
```

## 2. Download the project

Replace the placeholders with the repository's actual GitHub URL and the directory created by Git:

```bash
git clone <repository-url>
cd <repository-directory>
```

Run the remaining project commands from this directory.

## 3. Configure the environment

Create the local environment file from the safe template:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholders for these required values:

```dotenv
DB_NAME=<database-name>
DB_USER=<database-user>
DB_PASSWORD=<strong-database-password>
BIRDWEATHER_AUTH_KEY=<birdweather-auth-key>
```

Keep `.env` private and do not commit it.

## 4. Build and start the normal stack

```bash
docker compose up --build -d
```

This starts the normal services. The manual `historical-ingestion` service does not run during a normal startup.

## 5. Verify the deployment

Check service status:

```bash
docker compose ps
```

Review logs for the full stack or an individual service:

```bash
docker compose logs --tail=100
docker compose logs --tail=100 web
docker compose logs --tail=100 ingestion
```

To follow new log messages, add `-f` and press `Ctrl+C` when finished.

From Jeff's server, verify that the dashboard responds locally:

```bash
curl http://127.0.0.1:5000/
```

## 6. Run historical ingestion when needed

With the normal stack running, start the manual historical-ingestion job with:

```bash
docker compose --profile manual run --rm historical-ingestion
```

The job exits after it finishes. It is not part of normal `docker compose up` behavior.

## 7. Configure Nginx

Use `deploy/nginx/living-classroom.conf.template` as the starting point:

1. Copy it to the server's appropriate Nginx site-configuration location.
2. Replace `YOUR_DOMAIN` with the purchased domain or subdomain when it is known.
3. Enable the site using the method appropriate for the server's Linux distribution.
4. Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

The template listens for HTTP requests and proxies them to `http://127.0.0.1:5000`.

> **Later: domain, DNS, and HTTPS**
>
> Do not finalize the Nginx domain setting until the domain has been purchased. Once available, point its DNS records to Jeff's server, replace `YOUR_DOMAIN`, verify HTTP access, and then configure an HTTPS certificate. HTTPS is intentionally not included in the current template.

## 8. Stop or restart safely

Stop containers without removing them:

```bash
docker compose stop
```

Start stopped containers again:

```bash
docker compose start
```

Restart the running application stack:

```bash
docker compose restart
```

Stop and remove the Compose containers and network:

```bash
docker compose down
```

The PostgreSQL data remains in its named Docker volume. Do not add `--volumes` unless deleting the database is intentional.
