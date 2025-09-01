# Makefile for flog-otlp development with uv
.PHONY: help install test lint format check clean docker

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync --group dev

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov=flog_otlp --cov-report=term-missing

lint:  ## Run linting (ruff check + mypy)
	uv run --group lint ruff check src/ tests/
	uv run --group lint mypy src/

format:  ## Format code with black and ruff
	uv run --group lint black src/ tests/
	uv run --group lint ruff format src/ tests/

check:  ## Run all checks (format, lint, test)
	$(MAKE) format lint test

clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:  ## Build the package
	uv build

docker:  ## Build Docker image
	docker build -t flog-otlp .

docker-uv:  ## Build Docker image with uv
	docker build -f Dockerfile.uv -t flog-otlp:uv .

run:  ## Run the application (example)
	uv run flog-otlp --help

dev-install:  ## Install in development mode
	uv sync --group dev