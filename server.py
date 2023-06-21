#python -m uvicorn server:app --reload

import sqlite3
import argparse  
import random
import string
import sqlite_helpers
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime, timedelta

app = FastAPI()

#maybe create the table if it doesnt already exist
sqlite_helpers.maybe_create_table("urldatabase.db")

@app.post("/create_url")
async def create_url(request: Request):

    urljson = await request.json()
    timestamp = datetime.now()

    if "url" not in urljson:
        raise HTTPException(status_code=400, detail="URL required.")

    if "alias" not in urljson:
        aliasVal = generate_alias()
    else:
        aliasVal = urljson['alias']

    if sqlite_helpers.insert_url("urldatabase.db", urljson['url'], aliasVal):
        url_data = {"url": urljson['url'], "alias": aliasVal, "timestamp": timestamp, "message": "URL added successfully"}
        return url_data
    else:
        raise HTTPException(status_code=409, detail="alias taken nerd")
    
    

@app.get("/get_urls")
async def get_all_urls():
    return sqlite_helpers.get_urls("urldatabase.db")


@app.get("/get_url/{alias}")
async def get_url(alias: str):

    url_output = sqlite_helpers.get_url("urldatabase.db", alias)
    if url_output is None:
        raise HTTPException(status_code=404, detail="URL not found.")
    
    return RedirectResponse(url_output)
    

@app.post("/delete_url/{alias}")
async def delete_url(alias: str):
    if(sqlite_helpers.delete_url("urldatabase.db", alias)):
        return {"message": "URL deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="URL not found.")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 400:
        return HTMLResponse(content="<h1>URL required.</h1>", status_code=400)
    if exc.status_code == 409:
        return HTMLResponse(content="<h1>Alias already exists.</h1>", status_code=409)
    if exc.status_code == 404:
        customcontent = """
        <html>
            <head>
                <title>404 Error</title>
                <style>
                    body {
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .h1-container {
                        margin-top: 40vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                        font-family: Arial, sans-serif;
                    }

                    .h2-container {
                        margin-top: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                        font-family: Arial, sans-serif;
                    }

                    h1 {
                        font-size: 36px;
                    }

                    h2 {
                        font-size: 24px;
                    }
                </style>
            </head>
            <div class="h1-container">
                <h1>404 Error</h1>
                </div class="h2-container">
                    <h2>URL Not Found</h2>
                </div>
            </div>
            
            
        </html>
        """
        return HTMLResponse(content =customcontent, status_code=404)
    
    return exc
    

def generate_alias():
    idLength = 5
    charOptions = string.ascii_letters + string.digits #lowercase, uppercase, and numbers
    aliasID = ''.join(random.choices(charOptions, k=idLength))
    return aliasID

