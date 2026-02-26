FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install dependencies and curl for healthcheck
COPY requirements.txt .
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Create app directory
RUN mkdir -p /app/defaults/config

# Copy application code
COPY . .

# Copy config files to defaults
RUN cp config/alembic.ini /app/defaults/config/alembic.ini && \
    cp config/config.json.example /app/defaults/config/config.json.example && \
    chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["python", "run.py"]
