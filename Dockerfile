# Precision Agriculture Platform - Docker Image
# 
# Build: docker build -t precision-api:latest .
# Run: docker run -p 5000:5000 precision-api:latest

FROM python:3.11-slim

# Install curl for healthchecks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY mocks/ ./mocks/
COPY README.md .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "5000"]
