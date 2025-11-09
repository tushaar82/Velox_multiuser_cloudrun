# Multi-stage build for Analytics Service
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY shared/ /app/shared/
COPY analytics_service/ /app/analytics_service/
COPY api_gateway/analytics_routes.py /app/api_gateway/analytics_routes.py
COPY api_gateway/analytics_service.py /app/api_gateway/analytics_service.py
COPY api_gateway/middleware.py /app/api_gateway/middleware.py

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Run the application
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8082", "--workers", "2", "--timeout", "120", "analytics_service.app:app"]
