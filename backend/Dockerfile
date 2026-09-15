FROM python:3.11-slim

WORKDIR /app

# System deps needed later for psycopg (Phase 2) - installing now avoids
# a rebuild-from-scratch when we add SQLAlchemy.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
