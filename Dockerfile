# Small, explicit image — Railway's Dockerfile deploy path builds this directly,
# giving predictable behavior instead of relying on autodetected build steps.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Railway injects $PORT at runtime — the app must bind to it, not a hardcoded port.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
