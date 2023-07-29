FROM python:3.9-slim-buster

WORKDIR /src

RUN apt-get update && apt-get install -y default-libmysqlclient-dev

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["python", "server.py"]
