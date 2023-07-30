from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import prometheus_client
import uvicorn


from args import get_args
from generate_alias import generate_alias
import sqlite_helpers
from constants import HttpResponse, http_code_to_enum

app = FastAPI()
args = get_args()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

url_count = prometheus_client.Counter(
    "url_count",
    "Number of urls in the database",
)

sql_error_count = prometheus_client.Counter(
    "sql_error_count",
    "Number of sql errors that have occurred",
)

find_count = prometheus_client.Counter(
    "find_count",
    "Number of urls successfully found",
)

query_time = prometheus_client.Histogram(
    "query_time",
    "Time taken to execute SQLite queries",
    buckets=[0.1, 0.5, 1, 5],
)

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
            url_count.inc(1)
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
    start_time = time.time()
    logging.debug(f"/find called with alias: {alias}")
    url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
    elapsed_time = time.time() - start_time
    query_time.observe(elapsed_time)

    if url_output is None:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    find_count.inc(1)
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
    sql_error_count.inc(1)
    status_code_enum = http_code_to_enum[exc.status_code]
    return HTMLResponse(content=status_code_enum.content, status_code=status_code_enum.code)

@app.get("/metrics")
def get_metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest(),
    )

logging.Formatter.converter = time.gmtime

logging.basicConfig(
    # in mondo we trust
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level= logging.ERROR - (args.verbose*10),
)

if __name__ == "__main__":
    logging.info(f"running on {args.host}, listening on port {args.port}")
    initial_url_count = sqlite_helpers.get_number_of_entries(DATABASE_FILE)
    logging.info(f"number of urls in the database is {initial_url_count}")
    url_count.inc(initial_url_count)
    uvicorn.run(app, host=args.host, port=args.port)
