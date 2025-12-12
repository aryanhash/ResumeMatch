#!/bin/bash

# Kestra Deployment Script
# Usage: ./deploy-kestra.sh [local|production|stop]

set -e

KESTRA_IMAGE="kestra/kestra:latest"
KESTRA_PORT="${KESTRA_PORT:-8080}"
KESTRA_CONTAINER="kestra-resumematch"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_status "Docker is installed and running"
}

deploy_local() {
    print_status "Deploying Kestra locally..."
    
    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        print_warning "Stopping existing Kestra container..."
        docker stop ${KESTRA_CONTAINER} 2>/dev/null || true
        docker rm ${KESTRA_CONTAINER} 2>/dev/null || true
    fi
    
    # Create data directory if it doesn't exist
    mkdir -p ./kestra-data
    
    # Run Kestra container
    print_status "Starting Kestra container..."
    docker run -d \
        --name ${KESTRA_CONTAINER} \
        -p ${KESTRA_PORT}:8080 \
        -v "$(pwd)/kestra:/app/flows" \
        -v "$(pwd)/kestra-data:/app/.kestra" \
        -e KESTRA_CONFIGURATION_FILE=/app/flows/kestra-config.yml \
        ${KESTRA_IMAGE} \
        server standalone
    
    # Wait for Kestra to start
    print_status "Waiting for Kestra to start..."
    sleep 5
    
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        print_status "✅ Kestra is running!"
        print_status "🌐 Access Kestra UI at: http://localhost:${KESTRA_PORT}"
        print_warning "⚠️  Default credentials: admin / password (change immediately!)"
        print_status "📊 View logs: docker logs -f ${KESTRA_CONTAINER}"
    else
        print_error "Failed to start Kestra container"
        docker logs ${KESTRA_CONTAINER}
        exit 1
    fi
}

deploy_production() {
    print_status "Deploying Kestra for production..."
    
    # Check for required environment variables
    if [ -z "$KESTRA_ENCRYPTION_KEY" ]; then
        print_warning "KESTRA_ENCRYPTION_KEY not set. Generating one..."
        export KESTRA_ENCRYPTION_KEY=$(openssl rand -hex 32)
        print_status "Generated encryption key: ${KESTRA_ENCRYPTION_KEY}"
        print_warning "⚠️  Save this key securely!"
    fi
    
    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        print_warning "Stopping existing Kestra container..."
        docker stop ${KESTRA_CONTAINER} 2>/dev/null || true
        docker rm ${KESTRA_CONTAINER} 2>/dev/null || true
    fi
    
    # Create data directory if it doesn't exist
    mkdir -p ./kestra-data
    
    # Run Kestra container with production settings
    print_status "Starting Kestra container (production mode)..."
    docker run -d \
        --name ${KESTRA_CONTAINER} \
        --restart unless-stopped \
        -p ${KESTRA_PORT}:8080 \
        -v "$(pwd)/kestra:/app/flows" \
        -v "$(pwd)/kestra-data:/app/.kestra" \
        -e MICRONAUT_CONFIG_FILES=/app/flows/kestra-production.yml \
        -e KESTRA_ENCRYPTION_KEY=${KESTRA_ENCRYPTION_KEY} \
        ${KESTRA_IMAGE} \
        server standalone
    
    # Wait for Kestra to start
    print_status "Waiting for Kestra to start..."
    sleep 5
    
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        print_status "✅ Kestra is running in production mode!"
        print_status "🌐 Access Kestra UI at: http://localhost:${KESTRA_PORT}"
        print_warning "⚠️  Remember to:"
        print_warning "   1. Change default password"
        print_warning "   2. Set up HTTPS (reverse proxy)"
        print_warning "   3. Configure firewall rules"
        print_status "📊 View logs: docker logs -f ${KESTRA_CONTAINER}"
    else
        print_error "Failed to start Kestra container"
        docker logs ${KESTRA_CONTAINER}
        exit 1
    fi
}

stop_kestra() {
    print_status "Stopping Kestra..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        docker stop ${KESTRA_CONTAINER}
        print_status "✅ Kestra stopped"
    else
        print_warning "Kestra container is not running"
    fi
}

show_status() {
    print_status "Kestra Status:"
    
    if docker ps --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        print_status "✅ Container is running"
        docker ps --filter "name=${KESTRA_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        # Check if Kestra is responding
        if curl -s http://localhost:${KESTRA_PORT}/api/v1/configs > /dev/null 2>&1; then
            print_status "✅ Kestra API is responding"
        else
            print_warning "⚠️  Kestra API is not responding (may still be starting)"
        fi
    else
        print_warning "Container is not running"
    fi
}

show_logs() {
    if docker ps --format '{{.Names}}' | grep -q "^${KESTRA_CONTAINER}$"; then
        docker logs -f ${KESTRA_CONTAINER}
    else
        print_error "Kestra container is not running"
        exit 1
    fi
}

# Main script logic
check_docker

case "${1:-local}" in
    local)
        deploy_local
        ;;
    production)
        deploy_production
        ;;
    stop)
        stop_kestra
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 [local|production|stop|status|logs]"
        echo ""
        echo "Commands:"
        echo "  local      - Deploy Kestra locally (default)"
        echo "  production - Deploy Kestra for production"
        echo "  stop       - Stop Kestra container"
        echo "  status     - Show Kestra status"
        echo "  logs       - Show Kestra logs"
        exit 1
        ;;
esac

