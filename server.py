from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import prometheus_client
import uvicorn

from modules.args import get_args
from modules.generate_alias import generate_alias
import modules.sqlite_helpers as sqlite_helpers
from modules.constants import HttpResponse, http_code_to_enum
from modules.metrics import MetricsHandler

ROWS_PER_PAGE = 10

app = FastAPI()
args = get_args()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

metrics_handler = MetricsHandler.instance()

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
        if not alias.isalnum():
            raise ValueError("alias must only contain alphanumeric characters")

        with MetricsHandler.query_time.labels("create").time():
            if sqlite_helpers.insert_url(DATABASE_FILE, urljson['url'], alias):
                MetricsHandler.url_count.inc(1)
                return { "url": urljson['url'], "alias": alias }
            else:
                raise HTTPException(status_code=HttpResponse.CONFLICT.code )
    except KeyError:
        logging.exception("returning 400 due to missing key")
        raise HTTPException(status_code=HttpResponse.BAD_REQUEST.code)
    except ValueError:
        logging.exception(f"returning 422 due to invalid alias of \"{alias}\"")
        raise HTTPException(status_code=HttpResponse.INVALID_ARGUMENT_EXCEPTION.code)

@app.get("/list")
async def get_all_urls(search: Optional[str] = None, page: Optional[int] = 1):
    if page is None or page < 1:
        raise HTTPException(status_code=400, detail="Invalid page number")
    with MetricsHandler.query_time.labels("list").time():
        if search:
            return sqlite_helpers.search(DATABASE_FILE, search, page, ROWS_PER_PAGE)
        else:
            return sqlite_helpers.get_urls(DATABASE_FILE, page, ROWS_PER_PAGE)

async def get_url(alias: str):
    logging.debug(f"/find called with alias: {alias}")
    with MetricsHandler.query_time.labels("find").time():
        url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)

    if url_output is None:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    return RedirectResponse(url_output)


@app.post("/delete/{alias}")
async def delete_url(alias: str):
    logging.debug(f"/delete called with alias: {alias}")
    with MetricsHandler.query_time.labels("delete").time():
      if(sqlite_helpers.delete_url(DATABASE_FILE, alias)):
          return {"message": "URL deleted successfully"}
      else:
          raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    status_code_enum = http_code_to_enum[exc.status_code]
    MetricsHandler.http_error_codes.labels(status_code_enum.code).inc(1)
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

# we have a separate __name__ check here due to how FastAPI starts
# a server. the file is first ran (where __name__ == "__main__")
# and then calls `uvicorn.run`. the call to run() reruns the file,
# this time __name__ == "server". the separate __name__ if statement
# is so the thread references the same instance as the global
# metrics_handler referenced by the rest of the file. otherwise,
# the thread interacts with an instance different than the one the
# server uses
if __name__ == "server":
    initial_url_count = sqlite_helpers.get_number_of_entries(DATABASE_FILE)
    MetricsHandler.url_count.inc(initial_url_count)

if __name__ == "__main__":
    logging.info(f"running on {args.host}, listening on port {args.port}")
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)
