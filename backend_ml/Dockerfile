# backend_chatboy/Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend_chatboy_requirements.txt /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* /tmp/*

COPY src /app/src
ENV PYTHONPATH=/app/src

EXPOSE 8001
CMD ["uvicorn", "matprop_ml.chatbot.interface:app", "--host", "0.0.0.0", "--port", "8001"]
