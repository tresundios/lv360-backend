.PHONY: up down logs build test migrate shell clean rebuild seed seed-reset setup deploy-dev network-create

# Local development
up:
	docker compose -f docker-compose.local.yml --env-file .env.local up -d --remove-orphans

up-build:
	docker compose -f docker-compose.local.yml --env-file .env.local up -d --build --remove-orphans

down:
	docker compose -f docker-compose.local.yml --env-file .env.local down --remove-orphans

logs:
	docker compose -f docker-compose.local.yml logs -f

build:
	docker compose -f docker-compose.local.yml build

rebuild: down up-build

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

seed:
	@echo "[SEED] Running database seed..."
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend python -m app.db.seed

seed-reset:
	@echo "[SEED] Resetting and re-seeding database..."
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend python -m app.db.seed --reset

validate-seed:
	@echo "[VALIDATE] Running PF-004 acceptance criteria validation..."
	docker compose -f docker-compose.local.yml --env-file .env.local exec -e PYTHONPATH=/app backend python /app/scripts/validate_seed.py

# Backend specific commands
test:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend pytest

test-seed:
	@echo "[TEST] Running PF-004 unit tests..."
	docker compose -f docker-compose.local.yml --env-file .env.local exec -e PYTHONPATH=/app backend pytest /app/tests/test_pf004_seed.py -v

shell:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend bash

python:
	docker compose -f docker-compose.local.yml --env-file .env.local exec backend python

# Production deployment
network-create:
	docker network create lv360-shared-network 2>/dev/null || echo "Network already exists"

deploy-dev: network-create
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

# Development setup — force no-cache build, start all services, migrate and seed
setup:
	@echo "Setting up backend development environment..."
	docker compose -f docker-compose.local.yml --env-file .env.local down --remove-orphans
	docker compose -f docker-compose.local.yml --env-file .env.local build --no-cache backend
	docker compose -f docker-compose.local.yml --env-file .env.local up -d --remove-orphans
	@echo "Waiting for backend to be ready (up to 60s)..."
	@for i in $$(seq 1 30); do \
		docker compose -f docker-compose.local.yml exec backend python -c "print('ok')" 2>/dev/null && break; \
		echo "  attempt $$i/30..."; sleep 2; \
	done
	$(MAKE) migrate
	$(MAKE) seed
	@echo "Backend development environment ready!"
