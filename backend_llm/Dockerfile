FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

COPY requirements.txt /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/ /app/

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
