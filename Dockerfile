FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn neo4j python-dotenv httpx pydantic-settings

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY main.py .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
