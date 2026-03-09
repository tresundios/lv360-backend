#!/bin/bash

echo "🚀 Setting up LV360 Backend development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p logs data backups

# Copy environment file if it doesn't exist
if [ ! -f .env.local ]; then
    cp .env.local.example .env.local
    echo "✅ Created .env.local from example"
fi

# Build and start database services first
echo "📦 Building Docker images..."
docker compose -f docker-compose.local.yml --env-file .env.local build

echo "🚀 Starting database services..."
docker compose -f docker-compose.local.yml --env-file .env.local up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for database to start..."
sleep 10

# Check if database is ready
if docker compose -f docker-compose.local.yml --env-file .env.local exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "❌ Database failed to start. Check logs with 'make logs'"
    exit 1
fi

# Run migrations
echo "🔄 Running database migrations..."
docker compose -f docker-compose.local.yml --env-file .env.local exec backend alembic upgrade head

# Seed database
echo "🌱 Seeding database..."
docker compose -f docker-compose.local.yml --env-file .env.local exec backend python -m app.db.seed

# Start backend service
echo "🚀 Starting backend service..."
docker compose -f docker-compose.local.yml --env-file .env.local up -d backend

# Wait for backend to be ready
echo "⏳ Waiting for backend to start..."
sleep 10

# Check if backend is running
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running at http://localhost:8000"
else
    echo "❌ Backend failed to start. Check logs with 'make logs'"
    exit 1
fi

echo ""
echo "🎉 Backend development environment is ready!"
echo ""
echo "📝 Available commands:"
echo "  make up          - Start all services"
echo "  make down        - Stop all services"
echo "  make logs        - View logs"
echo "  make test        - Run tests"
echo "  make migrate     - Run migrations"
echo "  make shell       - Access backend shell"
echo "  make health      - Check health status"
echo ""
echo "🌐 API endpoints:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "🗄️ Database:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
