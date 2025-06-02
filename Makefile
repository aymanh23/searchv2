# Makefile for managing the FastAPI application and Docker container

# Variables
IMAGE_NAME := crewai-fastapi-service
TAG := latest
DOCKERFILE := Dockerfile

# Default target
.PHONY: all
all: build

# Build the Docker image
.PHONY: build
build:
	@echo "Building Docker image $(IMAGE_NAME):$(TAG)..."
	docker build -t $(IMAGE_NAME):$(TAG) -f $(DOCKERFILE) .
	@echo "Docker image $(IMAGE_NAME):$(TAG) built successfully."

# Run the Docker container
.PHONY: run
run:
	@echo "Running Docker container $(IMAGE_NAME):$(TAG) on port 8000..."
	docker run -p 8000:8000 --env-file .env $(IMAGE_NAME):$(TAG)
	@echo "Container stopped."

# Stop and remove all running containers (useful for cleanup)
.PHONY: stop-all
stop-all:
	@echo "Stopping and removing all running Docker containers..."
	docker ps -q | xargs -r docker stop
	docker ps -aq | xargs -r docker rm
	@echo "Done."

# Placeholder for linting (e.g., with flake8 or ruff)
.PHONY: lint
lint:
	@echo "Linting the codebase... (Not yet implemented)"
	# Example: ruff check .

# Placeholder for running tests (e.g., with pytest)
.PHONY: test
test:
	@echo "Running tests... (Not yet implemented)"
	# Example: pytest

# Clean Docker images (use with caution)
.PHONY: clean-images
clean-images:
	@echo "Removing Docker image $(IMAGE_NAME):$(TAG)... (Use with caution)"
	docker rmi $(IMAGE_NAME):$(TAG)
	@echo "Done."

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make build         - Build the Docker image"
	@echo "  make run           - Run the Docker container locally"
	@echo "  make stop-all      - Stop and remove all running Docker containers"
	@echo "  make lint          - Lint the codebase (placeholder)"
	@echo "  make test          - Run tests (placeholder)"
	@echo "  make clean-images  - Remove the built Docker image (use with caution)"
	@echo "  make help          - Show this help message"
