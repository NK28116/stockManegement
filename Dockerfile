# Base Image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first to leverage cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Ensure we copy the python package structure correctly
COPY . .

# Cloud Run defaults to port 8080
EXPOSE 8080

# Entrypoint
# Explicitly list the command to ensure no shell issues and correct variable expansion if shell form used, 
# but here using shell form to ensure $PORT is picked up by uvicorn command line if it was raw string.
# Actually, array form is preferred. We will use `sh -c` to allow expansion.
CMD ["sh", "-c", "uvicorn python.web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
