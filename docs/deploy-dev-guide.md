# Dev Environment Deployment Guide — dev.lamviec360.com

**Target environment:** `dev.lamviec360.com` / `appdev.lamviec360.com`  
**Docker registry:** Docker Hub — `navistresundios/lamviec360-backend`  
**Deploy trigger:** Manual Jenkins job  
**Compose file:** `docker-compose.dev.yml`  
**Image tag:** `dev-latest`

---

## Architecture Overview

```
Developer machine
      │
      │  git push  (any branch)
      ▼
  Jenkins (manual trigger)
      │
      ├─ 1. git pull latest code
      ├─ 2. docker build  (Dockerfile.prod, python:3.11-slim)
      ├─ 3. docker push   → Docker Hub  navistresundios/lamviec360-backend:dev-latest
      └─ 4. SSH → dev server
                │
                ├─ docker compose pull
                ├─ docker compose up -d
                ├─ alembic upgrade head
                └─ (optional) seed
```

**Services running on dev server:**

| Container | Image | Port |
|-----------|-------|------|
| `lv360_backend_dev` | `navistresundios/lamviec360-backend:dev-latest` | 8000 |
| `lv360_postgres_dev` | `postgres:15-alpine` | 5432 |
| `lv360_redis_dev` | `redis:7-alpine` | 6379 |
| `lv360_pg_backup_dev` | `postgres:15-alpine` | — |

---

## Prerequisites

### On developer machine
- Docker Desktop installed and running
- Docker Hub account with push access to `navistresundios`
- Access to Jenkins at your Jenkins URL

### On dev server (one-time setup)
```bash
# Install Docker + Docker Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Create app directory
mkdir -p /opt/lv360-backend
cd /opt/lv360-backend

# Copy required files from repo
scp docker-compose.dev.yml user@dev.lamviec360.com:/opt/lv360-backend/
scp .env.dev              user@dev.lamviec360.com:/opt/lv360-backend/

# Create backups directory
mkdir -p /opt/lv360-backend/backups
```

### `.env.dev` file on dev server
Create `/opt/lv360-backend/.env.dev` with real values (never commit this file):

```env
# Database
DATABASE_URL=postgresql://postgres:lv360_dev_password@postgres:5432/lv360
POSTGRES_DB=lv360
POSTGRES_USER=postgres
POSTGRES_PASSWORD=lv360_dev_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379

# Security — change this to a strong random string
JWT_SECRET=CHANGE_ME_USE_STRONG_RANDOM_SECRET

# CORS
CORS_ORIGINS=https://appdev.lamviec360.com,https://dev.lamviec360.com

# App
ENVIRONMENT=development
OTP_TTL_MINUTES=10
```

---

## Step 1 — Build and Push Docker Image (Developer Machine)

```bash
# From repo root
cd lv360-backend/backend

# Login to Docker Hub
docker login

# Build production image (uses Dockerfile.prod, python:3.11-slim)
docker build \
  -f Dockerfile.prod \
  -t navistresundios/lamviec360-backend:dev-latest \
  .

# Push to Docker Hub
docker push navistresundios/lamviec360-backend:dev-latest
```

Or via Makefile shortcut (if added):
```bash
make push-dev
```

---

## Step 2 — Trigger Jenkins Job

1. Open Jenkins → locate the `lv360-backend-deploy-dev` job
2. Click **Build Now**
3. Jenkins will:
   - Pull latest code from the configured branch
   - Build and tag the Docker image as `navistresundios/lamviec360-backend:dev-latest`
   - Push image to Docker Hub
   - SSH into `dev.lamviec360.com`
   - Run `docker compose pull` + `docker compose up -d`

**Expected Jenkins console output (success):**
```
[INFO] Building Docker image...
[INFO] Pushing to navistresundios/lamviec360-backend:dev-latest
[INFO] Deploying to dev.lamviec360.com...
[INFO] Running migrations...
[INFO] Deploy complete — http://dev.lamviec360.com:8000/health
```

---

## Step 3 — Manual Deploy on Dev Server (if Jenkins unavailable)

SSH into the dev server and run:

```bash
ssh user@dev.lamviec360.com
cd /opt/lv360-backend

# Pull latest image from Docker Hub
docker compose -f docker-compose.dev.yml pull

# Start / restart all services
docker compose -f docker-compose.dev.yml up -d --remove-orphans

# Verify all containers are running
docker compose -f docker-compose.dev.yml ps
```

**Expected output:**
```
NAME                   STATUS          PORTS
lv360_backend_dev      Up (healthy)    0.0.0.0:8000->8000/tcp
lv360_postgres_dev     Up (healthy)    0.0.0.0:5432->5432/tcp
lv360_redis_dev        Up (healthy)    0.0.0.0:6379->6379/tcp
lv360_pg_backup_dev    Up              —
```

---

## Step 4 — Run Database Migrations

```bash
ssh user@dev.lamviec360.com
cd /opt/lv360-backend

docker exec lv360_backend_dev alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 2026_04_11, auth tables
INFO  [alembic.runtime.migration] Done.
```

> **Important:** Always run migrations after every deployment that includes schema changes.

---

## Step 5 — Seed Test Data (optional, dev only)

```bash
docker exec lv360_backend_dev python -m app.db.seed
```

To reset and re-seed cleanly:
```bash
docker exec lv360_backend_dev python -m app.db.seed --reset
```

**This creates:**
- 1 `super_admin`, 2 `company_admin`, 3 `hr_recruiter`, 5 `job_seeker`
- 3 verified companies with 10 published jobs each
- Application pipeline data across all 6 stages
- All accounts use password: `Test1234!`

> **Note:** Do NOT seed on production. Dev only.

---

## Step 6 — Verify Deployment

```bash
# Health check
curl https://dev.lamviec360.com/health
# or
curl http://dev.lamviec360.com:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "environment": "development",
  "redis": true
}
```

**Swagger UI:**
```
http://dev.lamviec360.com:8000/docs
```

**Test login with seed account:**
```bash
curl -X POST http://dev.lamviec360.com:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@seed.lamviec360.com","password":"Test1234!"}'
```

---

## Rollback

If deployment fails or the app is broken:

```bash
ssh user@dev.lamviec360.com
cd /opt/lv360-backend

# Pull a specific previous image tag (replace with actual tag)
docker pull navistresundios/lamviec360-backend:dev-<previous-tag>

# Update compose to use that tag temporarily, then:
docker compose -f docker-compose.dev.yml up -d
```

Or simply re-trigger Jenkins with the previous known-good commit checked out.

---

## Logs and Debugging

```bash
# Backend app logs
docker logs lv360_backend_dev --tail 50 -f

# Check for OTP codes during testing
docker logs lv360_backend_dev --tail 20 | grep OTP

# Postgres logs
docker logs lv360_postgres_dev --tail 30

# Get a shell inside backend container
docker exec -it lv360_backend_dev bash

# Run a DB query directly
docker exec lv360_postgres_dev psql -U postgres -d lv360 \
  -c "SELECT role, COUNT(*) FROM users GROUP BY role;"
```

---

## Current State — What Is Deployed

As of the current codebase the following features are live on dev:

| Feature | Status | Endpoint |
|---------|--------|----------|
| Health check | ✅ Done | `GET /health` |
| User registration (step2 + OTP verify) | ✅ Done | `POST /api/v1/auth/register/step2` |
| Login (all roles) | ✅ Done | `POST /api/v1/auth/login` |
| 2FA login for company_admin | ✅ Done | `POST /api/v1/auth/login/2fa` |
| OTP resend | ✅ Done | `POST /api/v1/auth/otp/resend` |
| Token refresh | ✅ Done | `POST /api/v1/auth/refresh` |
| Logout | ✅ Done | `POST /api/v1/auth/logout` |
| Forgot / reset password | ✅ Done | `POST /api/v1/auth/forgot-password` |
| Get current user `/me` | ✅ Done | `GET /api/v1/auth/me` |
| First login complete | ✅ Done | `POST /api/v1/auth/first-login-complete` |
| Team invite (create / accept) | ✅ Done | `POST /api/v1/auth/invite` |
| AI abuse tracking | ✅ Done | `POST /api/v1/auth/ai-abuse` |
| Seed data (users, companies, jobs, apps) | ✅ Done | `make seed` / `python -m app.db.seed` |
| Companies / Jobs / Applications API | 🔲 Pending | Not yet implemented |
| Frontend integration | 🔲 Pending | — |

---

## Jenkins Pipeline Reference (Jenkinsfile skeleton)

If configuring Jenkins from scratch, the pipeline should contain these stages:

```groovy
pipeline {
  agent any
  environment {
    IMAGE = "navistresundios/lamviec360-backend:dev-latest"
    DEV_HOST = "user@dev.lamviec360.com"
    DEPLOY_DIR = "/opt/lv360-backend"
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Build Image') {
      steps {
        sh 'docker build -f backend/Dockerfile.prod -t $IMAGE backend/'
      }
    }
    stage('Push to Docker Hub') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', ...)]) {
          sh 'docker login -u $DOCKER_USER -p $DOCKER_PASS'
          sh 'docker push $IMAGE'
        }
      }
    }
    stage('Deploy to Dev Server') {
      steps {
        sshagent(['dev-server-ssh-key']) {
          sh """
            ssh $DEV_HOST '
              cd $DEPLOY_DIR &&
              docker compose -f docker-compose.dev.yml pull &&
              docker compose -f docker-compose.dev.yml up -d --remove-orphans &&
              docker exec lv360_backend_dev alembic upgrade head
            '
          """
        }
      }
    }
    stage('Health Check') {
      steps {
        sh 'curl -f http://dev.lamviec360.com:8000/health'
      }
    }
  }
}
```

> Store Docker Hub credentials in Jenkins → **Manage Credentials** → `dockerhub-creds`  
> Store SSH key in Jenkins → **Manage Credentials** → `dev-server-ssh-key`

---

## Quick Reference Commands

```bash
# Full fresh deploy (from dev server)
docker compose -f docker-compose.dev.yml pull
docker compose -f docker-compose.dev.yml up -d --remove-orphans
docker exec lv360_backend_dev alembic upgrade head
docker exec lv360_backend_dev python -m app.db.seed

# Restart backend only (after image update)
docker compose -f docker-compose.dev.yml pull backend
docker compose -f docker-compose.dev.yml up -d --no-deps backend

# Stop everything
docker compose -f docker-compose.dev.yml down

# Nuke data and start fresh (destructive!)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
docker exec lv360_backend_dev alembic upgrade head
docker exec lv360_backend_dev python -m app.db.seed
```
