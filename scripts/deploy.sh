#!/bin/bash

# Production deployment script for Website Scraper
# Usage: ./scripts/deploy.sh

set -e

echo "🚀 Starting deployment of Website Scraper..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

echo -e "${GREEN}✓${NC} Docker and Docker Compose are installed"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠${NC}  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created .env file. Please review and update if needed."
    else
        echo -e "${YELLOW}⚠${NC}  .env.example not found. Using default settings."
    fi
fi

# Stop existing containers
echo -e "${YELLOW}🛑${NC} Stopping existing containers..."
docker-compose down || true

# Build and start containers
echo -e "${GREEN}🔨${NC} Building Docker images..."
docker-compose build --no-cache

echo -e "${GREEN}🚀${NC} Starting containers..."
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳${NC} Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Services are running"
else
    echo -e "${RED}❌${NC} Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Check health endpoint
echo -e "${YELLOW}🏥${NC} Checking health endpoint..."
sleep 5

HEALTH_CHECK=$(curl -s http://localhost:8000/health || echo "failed")

if [[ "$HEALTH_CHECK" == *"healthy"* ]]; then
    echo -e "${GREEN}✓${NC} Health check passed"
else
    echo -e "${YELLOW}⚠${NC}  Health check may have failed. Check logs: docker-compose logs scraper"
fi

# Display service information
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📊 Service Information:"
echo "  - API URL: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Health Check: http://localhost:8000/health"
echo ""
echo "📝 Useful Commands:"
echo "  - View logs: docker-compose logs -f scraper"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - View status: docker-compose ps"
echo ""
echo -e "${GREEN}🎉 Ready to scrape!${NC}"

