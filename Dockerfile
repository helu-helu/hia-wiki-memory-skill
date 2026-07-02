FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn pinecone-client redis openai

# Copy application code
COPY api /app/api
COPY scripts /app/scripts

# Default wiki directory
ENV WIKI_DIR=/app/wiki
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
