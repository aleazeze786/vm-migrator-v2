
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# Ensure the 'app' package (in /app/backend/app) is importable as top-level 'app'
ENV PYTHONPATH=/app/backend
COPY backend /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
