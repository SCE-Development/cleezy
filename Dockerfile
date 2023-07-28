FROM python:3.9

RUN mkdir /src
WORKDIR /src

COPY requirements.txt .

RUN apt-get update && apt-get install -y default-libmysqlclient-dev
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install mysql-connector-python

COPY . .

EXPOSE 8000

CMD ["python", "server.py", "--database-file-path", "urldatabase.db", "-vvv"]