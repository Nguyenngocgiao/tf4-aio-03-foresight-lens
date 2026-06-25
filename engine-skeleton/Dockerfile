FROM python:3.13-slim

WORKDIR /app

# Serving deps only (training deps live in requirements-train.txt, not shipped)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code + pre-trained per-service baselines (local fallback; S3 in prod)
COPY app/ ./app/
COPY baselines/ ./baselines/

# Health check port per deployment-contract.md
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
