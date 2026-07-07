FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    USE_SECRET_MANAGER=1 \
    USE_CLOUD_SCHEDULER=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/entrypoint-gcp.sh /entrypoint-gcp.sh
RUN chmod +x /entrypoint-gcp.sh

COPY . .

RUN mkdir -p data

EXPOSE 8080

ENTRYPOINT ["/entrypoint-gcp.sh"]

CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", "--server.address=0.0.0.0", \
     "--server.headless=true"]
