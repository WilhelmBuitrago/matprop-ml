FROM ollama/ollama:latest

# Disable default ENTRYPOINT
ENTRYPOINT []

# Install Python + venv
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*
    

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY /src /app/ 

EXPOSE 8003
CMD ["sh", "-c", "ollama serve & uvicorn api.app:app --host 0.0.0.0 --port 8003"]