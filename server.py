from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import logging
import time
import uvicorn

from args import get_args
from generate_alias import generate_alias
import sqlite_helpers
from constants import HttpResponse, http_code_to_enum

app = FastAPI()
args = get_args()

#maybe create the table if it doesnt already exist
DATABASE_FILE = args.database_file_path
sqlite_helpers.maybe_create_table(DATABASE_FILE)

@app.post("/create_url")
async def create_url(request: Request):
    urljson = await request.json()
    logging.debug(f"/create_url called with body: {urljson}")
    alias = None

    try:
        alias = urljson.get('alias')
        if alias is None:
            if args.disable_random_alias:
                raise KeyError("alias must be specified")
            else:
                alias = generate_alias(urljson['url'])

        if sqlite_helpers.insert_url(DATABASE_FILE, urljson['url'], alias):
            return { "url": urljson['url'], "alias": alias }
        else:
            raise HTTPException(status_code=HttpResponse.CONFLICT.code )
    except KeyError:
        logging.exception("returning 400 due to missing key")
        raise HTTPException(status_code=HttpResponse.BAD_REQUEST.code)
   
@app.get("/list")
async def get_all_urls():
    return sqlite_helpers.get_urls(DATABASE_FILE)


@app.get("/find/{alias}")
async def get_url(alias: str):
    logging.debug(f"/find called with alias: {alias}")
    url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
    if url_output is None:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    
    return RedirectResponse(url_output)
    

@app.post("/delete/{alias}")
async def delete_url(alias: str):
    logging.debug(f"/delete called with alias: {alias}")
    if(sqlite_helpers.delete_url(DATABASE_FILE, alias)):
        return {"message": "URL deleted successfully"}
    else:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    status_code_enum = http_code_to_enum[exc.status_code]
    return HTMLResponse(content=status_code_enum.content, status_code=status_code_enum.code)

logging.Formatter.converter = time.gmtime

logging.basicConfig(
    # in mondo we trust
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level= logging.ERROR - (args.verbose*10),
)

if __name__ == "__main__":
    logging.info(f"running on {args.host}, listening on port {args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
