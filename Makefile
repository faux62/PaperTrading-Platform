# =========================
# PaperTrading Platform
# Makefile
# =========================

.PHONY: help install dev test lint build clean docker-up docker-down migrate

# Default target
help:
	@echo "PaperTrading Platform - Available Commands"
	@echo "==========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install all dependencies (backend + frontend)"
	@echo "  make install-backend  - Install backend dependencies only"
	@echo "  make install-frontend - Install frontend dependencies only"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start all services for development"
	@echo "  make dev-backend   - Start backend only (uvicorn)"
	@echo "  make dev-frontend  - Start frontend only (vite)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up     - Start Docker services (DB, Redis)"
	@echo "  make docker-down   - Stop Docker services"
	@echo "  make docker-logs   - Show Docker logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate       - Run database migrations"
	@echo "  make migrate-new   - Create new migration (usage: make migrate-new MSG='message')"
	@echo "  make db-reset      - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests only"
	@echo "  make test-frontend - Run frontend tests only"
	@echo "  make coverage      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Build:"
	@echo "  make build         - Build production artifacts"
	@echo "  make clean         - Clean build artifacts"

# =========================
# Installation
# =========================
install: install-backend install-frontend

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install

# =========================
# Development
# =========================
dev: docker-up
	@echo "🚀 Starting development environment..."
	@make -j2 dev-backend dev-frontend

dev-backend:
	@echo "🐍 Starting backend..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "⚛️  Starting frontend..."
	cd frontend && npm run dev

# =========================
# Docker
# =========================
docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose -f infrastructure/docker/docker-compose.dev.yml up -d
	@echo "✅ Services started!"
	@echo "   PostgreSQL: localhost:5432"
	@echo "   TimescaleDB: localhost:5433"
	@echo "   Redis: localhost:6379"
	@echo "   pgAdmin: http://localhost:5050"
	@echo "   Redis Commander: http://localhost:8081"

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker-compose -f infrastructure/docker/docker-compose.dev.yml down

docker-logs:
	docker-compose -f infrastructure/docker/docker-compose.dev.yml logs -f

docker-clean:
	@echo "🧹 Removing Docker volumes..."
	docker-compose -f infrastructure/docker/docker-compose.dev.yml down -v

# =========================
# Database
# =========================
migrate:
	@echo "🗄️  Running migrations..."
	cd backend && alembic upgrade head

migrate-new:
	@echo "📝 Creating new migration..."
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-reset:
	@echo "⚠️  Resetting database..."
	cd backend && alembic downgrade base
	cd backend && alembic upgrade head

# =========================
# Testing
# =========================
test: test-backend test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && pytest -v

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test

coverage:
	@echo "📊 Running tests with coverage..."
	cd backend && pytest --cov=app --cov-report=html
	@echo "Coverage report: backend/htmlcov/index.html"

# =========================
# Code Quality
# =========================
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting backend..."
	cd backend && black --check app
	cd backend && isort --check-only app
	cd backend && flake8 app

lint-frontend:
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

format:
	@echo "✨ Formatting code..."
	cd backend && black app
	cd backend && isort app
	cd frontend && npm run format

# =========================
# Build
# =========================
build: build-backend build-frontend

build-backend:
	@echo "🏗️  Building backend..."
	cd backend && pip install build && python -m build

build-frontend:
	@echo "🏗️  Building frontend..."
	cd frontend && npm run build

# =========================
# Cleanup
# =========================
clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov 2>/dev/null || true
	rm -rf frontend/dist 2>/dev/null || true
	@echo "✅ Cleaned!"
