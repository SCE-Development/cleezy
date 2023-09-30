FROM python:3.9-slim-buster

WORKDIR /app

RUN apt-get update && apt-get install -y default-libmysqlclient-dev

COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8000

ENTRYPOINT ["python", "server.py"]
