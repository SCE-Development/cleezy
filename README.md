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
