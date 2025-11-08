.PHONY: help setup install test clean docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make setup        - Run initial setup"
	@echo "  make install      - Install Python dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make clean        - Clean temporary files"
	@echo "  make docker-up    - Start infrastructure services"
	@echo "  make docker-down  - Stop infrastructure services"
	@echo "  make docker-logs  - View service logs"
	@echo "  make lint         - Run code linting"
	@echo "  make format       - Format code"

setup:
	@bash setup.sh

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=shared --cov-report=html --cov-report=term

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-ps:
	docker-compose ps

lint:
	@echo "Running flake8..."
	flake8 shared/ api_gateway/ websocket_service/ strategy_workers/ order_processor/ analytics_service/ market_data_engine/ --max-line-length=120

format:
	@echo "Formatting code with black..."
	black shared/ api_gateway/ websocket_service/ strategy_workers/ order_processor/ analytics_service/ market_data_engine/ tests/
