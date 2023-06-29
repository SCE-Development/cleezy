#python -m uvicorn server:app --reload

import sqlite_helpers
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime

from constants import HttpResponse, http_code_to_enum

app = FastAPI()

#maybe create the table if it doesnt already exist
DATABASE_FILE = "urldatabase.db"
sqlite_helpers.maybe_create_table(DATABASE_FILE)

@app.post("/create_url")
async def create_url(request: Request):

    urljson = await request.json()
    timestamp = datetime.now()

    if "url" not in urljson or "alias" not in urljson:
        raise HTTPException(status_code=404)

    if sqlite_helpers.insert_url(DATABASE_FILE, urljson['url'], urljson['alias']):
        return { "alias": urljson['alias'] }
    else:
        raise HTTPException(status_code=409 )
    
    

@app.get("/list")
async def get_all_urls():
    return sqlite_helpers.get_urls(DATABASE_FILE)


@app.get("/find/{alias}")
async def get_url(alias: str):

    url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
    if url_output is None:
        raise HTTPException(status_code=404)
    
    return RedirectResponse(url_output)
    

@app.post("/delete/{alias}")
async def delete_url(alias: str):
    if(sqlite_helpers.delete_url(DATABASE_FILE, alias)):
        return {"message": "URL deleted successfully"}
    else:
        raise HTTPException(status_code=404)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    status_code_enum = http_code_to_enum[exc.status_code]
    return HTMLResponse(content=status_code_enum.content, status_code=status_code_enum.code)

    