.PHONY: up down logs build test migrate shell clean

# Local development
up:
	docker compose -f docker-compose.local.yml --env-file .env.local up -d --remove-orphans

down:
	docker compose -f docker-compose.local.yml --env-file .env.local down --remove-orphans

logs:
	docker compose -f docker-compose.local.yml logs -f

build:
	docker compose -f docker-compose.local.yml build

clean:
	docker compose -f docker-compose.local.yml down -v
	docker system prune -f

# Database operations
migrate:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend alembic upgrade head

migrate-down:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend alembic downgrade -1

reset-db:
	docker compose -f docker-compose.local.yml --env-file .env.local exec postgres dropdb -U postgres lv360 || true
	docker compose -f docker-compose.local.yml --env-file .env.local exec postgres createdb -U postgres lv360
	$(MAKE) migrate

seed-db:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend python -m app.db.seed

# Backend specific commands
test:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend pytest

shell:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend bash

python:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend python

# Production deployment
deploy-dev:
	docker compose -f docker-compose.dev.yml --env-file .env.dev pull
	docker compose -f docker-compose.dev.yml --env-file .env.dev up -d

# Health check
health:
	curl -f http://localhost:8000/health || echo "Backend not ready"

# Backup and restore
backup:
	docker compose -f docker-compose.local.yml --env-file .env.local exec postgres pg_dump -U postgres lv360 > backup_$$(date +%Y%m%d_%H%M%S).sql

restore:
	@echo "Usage: make restore FILE=backup.sql"
	docker compose -f docker-compose.local.yml --env-file .env.local exec -T postgres psql -U postgres lv360 < $(FILE)

# Development setup
setup:
	@echo "Setting up backend development environment..."
	docker compose -f docker-compose.local.yml --env-file .env.local build
	docker compose -f docker-compose.local.yml --env-file .env.local up -d postgres redis
	sleep 5
	$(MAKE) migrate
	$(MAKE) seed-db
	docker compose -f docker-compose.local.yml --env-file .env.local up -d backend
	@echo "Backend development environment ready!"
