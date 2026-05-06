# LV360 Backend

FastAPI backend application for LamViec360 with PostgreSQL and Redis.

## Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development without Docker)
- Git

### Quick Start

1. **Clone and setup:**
```bash
git clone https://github.com/tresundios/lv360-backend.git
cd lv360-backend
cp .env.local.example .env.local
```

2. **Start with Docker:**
```bash
make setup
```

3. **Access the application:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432
- Redis: localhost:6379

### Development Commands

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down

# Run database migrations
make migrate

# Reset database
make reset-db

# Seed database
make seed-db

# Run tests
make test

# Access backend shell
make shell

# Access Python REPL
make python
```

### Database Operations

```bash
# Run migrations
make migrate

# Rollback migration
make migrate-down

# Reset database (dangerous!)
make reset-db

# Seed database with sample data
make seed-db

# Create new migration
docker compose -f docker-compose.local.yml --env-file .env.local exec backend alembic revision --autogenerate -m "description"
```

### Environment Variables

Copy `.env.local.example` to `.env.local` and configure:

```bash
COMPOSE_PROJECT_NAME=lv360_backend_dev
DATABASE_URL=postgresql://postgres:password@postgres:5432/lv360
REDIS_URL=redis://redis:6379
JWT_SECRET=your-jwt-secret-change-this-in-production
POSTGRES_PASSWORD=password
CORS_ORIGINS=http://localhost:3080,https://appdev.lamviec360.com
```

### Docker Compose Files

- `docker-compose.local.yml` - Local development
- `docker-compose.dev.yml` - Dev server deployment

### Project Structure

```
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   └── models/
├── alembic/
│   └── versions/
├── tests/
├── scripts/
│   └── entrypoint.sh
├── requirements.txt
├── Dockerfile.prod
└── alembic.ini
```

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/` - API v1 prefix
- `GET /docs` - Swagger documentation
- `GET /redoc` - ReDoc documentation

### Database

**PostgreSQL 15** with:
- Database: lv360
- User: postgres
- Password: (from .env.local)

**Redis 7** for caching and sessions.

### Deployment

Deploy to dev server:
```bash
make deploy-dev
```

### Backup and Restore

```bash
# Backup database
make backup

# Restore database
make restore FILE=backup_20260310_020000.sql
```

### CI/CD

Jenkins pipeline automatically:
1. Runs tests
2. Builds Docker image
3. Pushes to Docker Hub
4. Deploys to dev server
5. Runs database migrations

### Troubleshooting

**Port conflicts:**
- Backend uses port 8000
- Postgres uses port 5432
- Redis uses port 6379

**Database issues:**
```bash
# Check database connection
make shell
python -c "from app.database import SessionLocal; db = SessionLocal(); print('Database connected')"

# Reset if needed
make reset-db
```

**Migration issues:**
```bash
# Check current migration
make shell
alembic current

# Force migration to latest
make shell
alembic stamp head
```

**Container issues:**
```bash
# Check container status
docker ps

# View logs
make logs

# Restart services
make down && make up
```

### Local Development Without Docker

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Setup environment:
```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/lv360
export REDIS_URL=redis://localhost:6379
```

3. Run migrations:
```bash
alembic upgrade head
```

4. Start application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests if needed
5. Run tests and linting
6. Submit pull request

### License

MIT License - see LICENSE file for details.


### Complete fresh local setup sequence
```bash
# 1. Clone and enter
cd lv360-backend
 
# 2. Copy env file (first time only)
cp .env.example .env.local   # edit values as needed
 
# 3. Force clean build and start
make down
docker compose -f docker-compose.local.yml --env-file .env.local build --no-cache backend
make up
 
# 4. Migrate and seed
make migrate
make seed
 
# 5. Verify
docker logs lv360-backend --tail 5
curl http://localhost:8000/health
```

### Subsequent restarts (already built)

```bash
make down && make up
make migrate   # only needed after new migrations
```

### Reset everything

```bash
make down
make seed-reset
```

# Validate Seed

### 1. Rebuild with PyJWT fix (if not done yet)

```bash
make down
docker compose -f docker-compose.local.yml --env-file .env.local build --no-cache backend
make up
```

### 2. Migrate + seed

```bash
make migrate
make seed
```

### 3. Validate all 5 acceptance criteria
```bash
make validate-seed
```

### 4. Run only unit tests for PF-004
```bash
make down
docker compose -f docker-compose.local.yml --env-file .env.local build --no-cache backend
make up
make test-seed
```

