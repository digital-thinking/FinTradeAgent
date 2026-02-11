# Multi-stage production Dockerfile for FinTradeAgent

# Stage 1: Frontend Build
FROM node:18-alpine AS frontend-builder

# Set working directory
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy frontend source
COPY frontend/ ./

# Build for production
ENV VITE_API_BASE_URL=/api
ENV VITE_WS_BASE_URL=/ws
RUN npm run build:prod

# Stage 2: Backend Build
FROM python:3.11-slim AS backend-builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt ./
COPY backend/requirements.txt ./backend-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user -r backend-requirements.txt

# Stage 3: Production Runtime
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/appuser/.local/bin:$PATH"

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -s /bin/bash -c "App User" appuser
RUN mkdir -p /home/appuser && chown -R appuser:appgroup /home/appuser

# Install system runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=backend-builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup backend/ ./backend/

# Copy frontend build from frontend builder
COPY --from=frontend-builder --chown=appuser:appgroup /app/frontend/dist ./static/

# Copy production configuration
COPY --chown=appuser:appgroup .env.production ./.env
COPY --chown=appuser:appgroup scripts/start-production.sh ./

# Create necessary directories
RUN mkdir -p /var/log/fintradeagent /var/lib/fintradeagent && \
    chown -R appuser:appgroup /var/log/fintradeagent /var/lib/fintradeagent

# Make start script executable
RUN chmod +x start-production.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["./start-production.sh"]