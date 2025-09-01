# Multi-stage build for flog-otlp container
# Stage 1: Build flog binary with Go
FROM golang:1.21-alpine AS go-builder

# Install git (required for go install)
RUN apk add --no-cache git

# Install flog
RUN go install github.com/mingrammer/flog@latest

# Stage 2: Final runtime image with Python
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy flog binary from go-builder stage
COPY --from=go-builder /go/bin/flog /usr/local/bin/flog

# Set working directory
WORKDIR /app

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy project files
COPY pyproject.toml LICENSE README.md ./
COPY src/ src/

# Install the package (non-editable for container)
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash flog-user && \
    chown -R flog-user:flog-user /app

USER flog-user

# Set default command
ENTRYPOINT ["flog-otlp"]

# Default arguments (can be overridden)
CMD ["--help"]