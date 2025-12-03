#!/bin/bash
# ================================
# PaperTrading - Local Deploy Script
# ================================
# Script per gestire il deploy locale su Mac
# Uso: ./deploy-local.sh [start|stop|restart|status|logs|update]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.local.yml"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Trova IP locale
get_local_ip() {
    # Prova WiFi prima, poi Ethernet
    local ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
    echo "$ip"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║     📈 PaperTrading Platform           ║"
    echo "║        Local Deployment                ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker non installato. Installalo da https://docker.com"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker non in esecuzione. Avvia Docker Desktop."
        exit 1
    fi
}

start_services() {
    print_banner
    check_docker
    
    local LOCAL_IP=$(get_local_ip)
    export LOCAL_IP
    
    echo -e "${YELLOW}Avvio servizi...${NC}"
    echo ""
    
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    echo ""
    print_status "Servizi avviati!"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  L'applicazione è disponibile a:${NC}"
    echo ""
    echo -e "  🌐 Frontend:  ${BLUE}http://$LOCAL_IP${NC}"
    echo -e "  🔌 API:       ${BLUE}http://$LOCAL_IP:8000${NC}"
    echo -e "  📚 API Docs:  ${BLUE}http://$LOCAL_IP:8000/docs${NC}"
    echo ""
    echo -e "  Da questo Mac: ${BLUE}http://localhost${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    print_warning "Prima esecuzione? Attendi ~1 min per il build delle immagini."
}

stop_services() {
    print_banner
    check_docker
    
    echo -e "${YELLOW}Arresto servizi...${NC}"
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" down
    
    print_status "Servizi arrestati."
}

restart_services() {
    stop_services
    echo ""
    start_services
}

show_status() {
    print_banner
    check_docker
    
    echo -e "${YELLOW}Stato servizi:${NC}"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo -e "${YELLOW}Health checks:${NC}"
    
    # Check backend
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_status "Backend: healthy"
    else
        print_warning "Backend: non raggiungibile"
    fi
    
    # Check frontend
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        print_status "Frontend: healthy"
    else
        print_warning "Frontend: non raggiungibile"
    fi
}

show_logs() {
    check_docker
    
    local service="${2:-}"
    
    if [ -z "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
    else
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100 "$service"
    fi
}

update_services() {
    print_banner
    check_docker
    
    echo -e "${YELLOW}Aggiornamento servizi...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Pull latest code (if git)
    if [ -d ".git" ]; then
        print_status "Pull codice..."
        git pull
    fi
    
    # Rebuild and restart
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    print_status "Aggiornamento completato!"
}

cleanup() {
    print_banner
    check_docker
    
    echo -e "${YELLOW}Pulizia risorse Docker...${NC}"
    
    docker compose -f "$COMPOSE_FILE" down -v --rmi local
    docker system prune -f
    
    print_status "Pulizia completata."
}

show_help() {
    print_banner
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandi disponibili:"
    echo "  start    - Avvia tutti i servizi"
    echo "  stop     - Arresta tutti i servizi"
    echo "  restart  - Riavvia tutti i servizi"
    echo "  status   - Mostra stato dei servizi"
    echo "  logs     - Mostra logs (opzionale: logs [servizio])"
    echo "  update   - Aggiorna e riavvia i servizi"
    echo "  cleanup  - Rimuove container, volumi e immagini"
    echo "  help     - Mostra questo messaggio"
    echo ""
    echo "Servizi disponibili per logs:"
    echo "  backend, frontend, postgres, redis"
    echo ""
    echo "Esempio:"
    echo "  $0 start"
    echo "  $0 logs backend"
}

# Main
case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    update)
        update_services
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
