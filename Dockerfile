# Base Image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies (if any)
# For now, slim image should be sufficient for pure python deps. 
# If complex math libs are needed, we might need build-essential, but keeping clean for now.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first to leverage cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Assuming the root directory contains python/ folder
COPY . .

# Cloud Run defaults to port 8080
EXPOSE 8080

# Entrypoint
# Using shell form to allow variable expansion if needed, but array form is safer for signal handling.
# However, for Cloud Run $PORT expansion, shell form or explicit command is common.
# Note: Exec form ["cmd", "arg"] doesn't expand ENV vars.
# We will use the command string as requested in GoalToDeploy.md
CMD exec uvicorn python.web.app:app --host 0.0.0.0 --port $PORT
