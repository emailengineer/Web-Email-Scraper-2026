.PHONY: help build up down logs restart test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start services
	docker-compose up -d

down: ## Stop services
	docker-compose down

logs: ## View logs
	docker-compose logs -f scraper

restart: ## Restart services
	docker-compose restart

test: ## Run tests
	pytest

clean: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f

deploy: ## Deploy using deployment script
	./scripts/deploy.sh

