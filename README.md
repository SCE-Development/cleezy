# cleezy
sce url shortening service

## How to Run
- [ ] setup sce-cli using the steps here https://github.com/SCE-Development/SCE-CLI
- [ ] clone the project with
```
sce clone z
```
- [ ] link the project to the tool
```
cd PATH_TO_CLEEZY_HERE
sce link z
```
- [ ] run the project
```
sce run z
```
- [ ] ensure the server is running locally at `http://localhost:8000`

if youre running cleezy on sce.sjsu.edu, make an .env file like
```
CLEEZY_PASTE_API_KEY=NOTHING_REALLY
```

## APIs
### To add URL
send HTTP POST request to http://localhost:8000/create_url with body
```json
{
    "alias": "myurl",
    "url": "https://sce.sjsu.edu/"
}
```
### To access URL
Open http://localhost:8000/find/myurl in the browser

### To list URLs in the database
Open http://localhost:8000/list in the browser

### To delete a URL
- send HTTP POST request to http://localhost:8000/delete/myurl
- verify the url was deleted by opening http://localhost:8000/list in the browser

### To create a paste
if you didnt make an env file like above, no need to pass in api key
```sh
curl -X POST "http://localhost:8000/paste/create" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_secret_key_here" \
     -d '{"title": "My First Paste", "text": "hello2"}'

# example response is
# {"status":"success","id":"6556e","url":"/paste/6556e"}
```

### To view a paste
```sh
# put the paste id after the `/paste/` in the url, like below
curl http://localhost:8000/paste/6556e
```

## SQLite Migrations
If you have an existing database and want to add a column, see below
```sh
docker exec -it cleezy-app /bin/bash

apt update

apt install -y sqlite3

# for example adding a new expires_at column
ALTER TABLE urls
ADD COLUMN expires_at DATETIME DEFAULT NULL;
```
