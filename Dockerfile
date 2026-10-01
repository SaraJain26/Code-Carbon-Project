# ==========================================
# Stage 1: Build the React frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/dashboard

# Copy package descriptors first to leverage Docker layer caching
COPY dashboard/package*.json ./

# Install dependencies (use npm ci for clean reproducible builds)
RUN npm ci

# Copy the rest of the dashboard source code
COPY dashboard/ ./

# Build the production React app (generates dashboard/dist)
RUN npm run build

# ==========================================
# Stage 2: Create the Python production runtime
# ==========================================
FROM python:3.11-slim AS production-runtime
WORKDIR /app

# Install system dependencies (curl for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the project files needed to install the python application
# Note: .dockerignore guarantees that secret .env is NOT copied
COPY pyproject.toml requirements.txt ./

# Install python dependencies including fastapi and uvicorn explicitly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn python-multipart httpx && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# Copy the backend source code
# We explicitly copy only the src/ directory, ensuring .env is never copied
COPY src/ ./src/

# Copy the built static frontend files from Stage 1
COPY --from=frontend-builder /app/dashboard/dist ./dashboard/dist

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Run readiness healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD-SHELL curl -f "http://localhost:${PORT:-8000}/health" || exit 1

# Start the FastAPI server using Uvicorn
CMD ["sh", "-c", "exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
