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
## QR Embeds
### tl;dr THEY DON'T WORK ON DISCORD

here's the discord embed debugger that tries to scrape embed stuff from the url it is provided. 'internal error' means discord wasn't able to do this

<img width="394" height="400" alt="image" src="https://github.com/user-attachments/assets/adc83ef3-7d06-458b-8cc8-3569023559a6" />

here's some logs from cleezy-nginx after the embed debugger was run and a twitter post with the QR url was sent 
```
172.25.0.14 - - [01/Sep/2025:19:03:43 +0000] "GET /qr/EMBEDTEST1 HTTP/1.0" 404 185 "-" "Twitterbot/1.0"
172.25.0.14 - - [01/Sep/2025:19:03:43 +0000] "GET /qr/EMBEDTEST1 HTTP/1.0" 404 185 "-" "Twitterbot/1.0"
```
as you can see, only twitter was able to connect to the site and scrape, display embed stuff

<img width="695" height="391" alt="image" src="https://github.com/user-attachments/assets/1369dd42-09fa-4dda-9d0c-def44dbf3a0d" />

ATP, the source of the issue is not very apparent
