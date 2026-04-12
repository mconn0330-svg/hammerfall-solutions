FROM python:3.11-slim

WORKDIR /app

# Install dependencies first — layer caches unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

EXPOSE 8000

# config.yaml is mounted read-only via docker-compose volume.
# All URLs and keys come from environment variables — not baked into the image.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
