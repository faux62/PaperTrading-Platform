#!/bin/bash
#
# PaperTrading Platform - Database Reset Script
# This script completely resets the database and recreates all tables
#
# Usage:
#   ./reset_database.sh              # Reset DB using prod compose
#   ./reset_database.sh dev          # Reset DB using dev compose
#
# WARNING: This will DELETE ALL DATA in the database!
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Determine which docker-compose file to use
COMPOSE_FILE="infrastructure/docker/docker-compose.prod.yml"
if [ "$1" == "dev" ]; then
    COMPOSE_FILE="infrastructure/docker/docker-compose.dev.yml"
fi

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}  PaperTrading Database Reset Script  ${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""
echo -e "${RED}WARNING: This will DELETE ALL DATA in the database!${NC}"
echo ""
echo "Using compose file: $COMPOSE_FILE"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Stopping containers...${NC}"
docker compose -f $COMPOSE_FILE down

echo ""
echo -e "${YELLOW}Step 2: Removing database volume...${NC}"
docker volume rm docker_postgres_data 2>/dev/null || echo "Volume not found (this is OK)"

echo ""
echo -e "${YELLOW}Step 3: Starting fresh database...${NC}"
docker compose -f $COMPOSE_FILE up -d postgres redis

echo ""
echo -e "${YELLOW}Step 4: Waiting for database to be ready...${NC}"
sleep 5

# Wait for postgres to be healthy
for i in {1..30}; do
    if docker compose -f $COMPOSE_FILE exec -T postgres pg_isready -U papertrading_user -d papertrading > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

echo ""
echo -e "${YELLOW}Step 5: Running migrations to create all tables...${NC}"
docker compose -f $COMPOSE_FILE up migrations

echo ""
echo -e "${YELLOW}Step 6: Starting all services...${NC}"
docker compose -f $COMPOSE_FILE up -d

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Database reset complete!           ${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "The database has been recreated with all tables."
echo "You can now:"
echo "  1. Register a new user at http://localhost"
echo "  2. Create portfolios and start trading"
echo ""
