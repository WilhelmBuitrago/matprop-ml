from python:3.12-slim

RUN apt-get update && apt-get install -y git-lfs && git lfs install

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
#RUN python -m pip install --upgrade numpy
WORKDIR /app
COPY /src /app/ 

EXPOSE 8004
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8004"]