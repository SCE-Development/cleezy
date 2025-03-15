from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import prometheus_client
import uvicorn
from queue import Queue
from threading import Thread

from modules.args import get_args
from modules.generate_alias import generate_alias
import modules.sqlite_helpers as sqlite_helpers
from modules.constants import HttpResponse, http_code_to_enum
from modules.metrics import MetricsHandler
from modules.sqlite_helpers import increment_used_column
from modules.cache import Cache
from modules.qr_code import QRCode


app = FastAPI()
args = get_args()
alias_queue = Queue()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = Cache(args.cache_size)

# maybe create the table if it doesnt already exist
DATABASE_FILE = args.database_file_path
sqlite_helpers.maybe_create_table(DATABASE_FILE)
qr_code_cache = QRCode(
  base_url=args.qr_code_base_url,
  qr_cache_path=args.qr_code_cache_path,
  max_size=args.qr_code_cache_size,
  cache_state_file=args.qr_code_cache_state_file,
  qr_image_path=args.qr_code_center_image_path,
)


# middleware to get metrics on HTTP response codes
@app.middleware("http")
async def track_response_codes(request: Request, call_next):
    response = await call_next(request)
    status_code = response.status_code
    MetricsHandler.http_code.labels(request.url.path, status_code).inc()
    return response


@app.post("/create_url")
async def create_url(request: Request):
    urljson = await request.json()
    logging.debug(f"/create_url called with body: {urljson}")
    alias = None

    try:
        alias = urljson.get("alias")
        if alias is None:
            if args.disable_random_alias:
                raise KeyError("alias must be specified")
            else:
                alias = generate_alias(urljson["url"])
        if not alias.isalnum():
            raise ValueError("alias must only contain alphanumeric characters")
        expiration_date = urljson.get("expiration_date")

        with MetricsHandler.query_time.labels("create").time():
            response = sqlite_helpers.insert_url(
                DATABASE_FILE, urljson["url"], alias, expiration_date
            )
            if response is not None:
                MetricsHandler.url_count.inc(1)
                return {
                    "url": urljson["url"],
                    "alias": alias,
                    "created_at": response,
                    "expires_at": expiration_date,
                }
            else:
                raise HTTPException(status_code=HttpResponse.CONFLICT.code)
    except KeyError:
        logging.exception("returning 400 due to missing key")
        raise HTTPException(status_code=HttpResponse.BAD_REQUEST.code)
    except ValueError:
        logging.exception(f'returning 422 due to invalid alias of "{alias}"')
        raise HTTPException(status_code=HttpResponse.INVALID_ARGUMENT_EXCEPTION.code)


@app.get("/list")
async def get_urls(
    search: Optional[str] = None,
    page: int = 0,
    sort_by: str = "created_at",
    order: str = "DESC",
):
    valid_sort_attributes = {"id", "url", "alias", "created_at", "used"}
    if order not in {"DESC", "ASC"}:
        raise HTTPException(status_code=400, detail="Invalid order")
    if sort_by not in valid_sort_attributes:
        raise HTTPException(status_code=400, detail="Invalid sorting attribute")
    if page < 0:
        raise HTTPException(status_code=400, detail="Invalid page number")
    if search and not search.isalnum():
        raise HTTPException(
            status_code=400,
            detail=f'search term "{search}" is invalid. only alphanumeric chars are allowed',
        )
    with MetricsHandler.query_time.labels("list").time():
        urls = sqlite_helpers.get_urls(
            DATABASE_FILE, page, search=search, sort_by=sort_by, order=order
        )
        total_urls = sqlite_helpers.get_number_of_entries(DATABASE_FILE, search=search)
        return {
            "data": urls,
            "total": total_urls,
            "rows_per_page": sqlite_helpers.ROWS_PER_PAGE,
        }


@app.get("/find/{alias}")
async def get_url(alias: str):
    logging.debug(f"/find called with alias: {alias}")
    url_output = cache.find(alias)  # try to find url in cache
    if url_output is not None:
        alias_queue.put(alias)
        return RedirectResponse(url_output)

    with MetricsHandler.query_time.labels("find").time():
        url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
    if url_output is None:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    cache.add(alias, url_output)  # else, adds url and alias to cache

    alias_queue.put(alias)
    return RedirectResponse(url_output)


@app.post("/delete/{alias}")
async def delete_url(alias: str):
    logging.debug(f"/delete called with alias: {alias}")
    with MetricsHandler.query_time.labels("delete").time():
        if sqlite_helpers.delete_url(DATABASE_FILE, alias):
            qr_code_cache.delete(alias)
            cache.delete(alias)
            return {"message": "URL deleted successfully"}
        else:
            raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)

@app.get("/qr/{alias}") 
async def qr(alias: str):
    logging.debug(f"/qr code generation called with alias: {alias}")
    with MetricsHandler.query_time.labels("qr").time():
        maybe_image_data = qr_code_cache.find(alias)
        if maybe_image_data is not None:
            return FileResponse(
            maybe_image_data,
            media_type='image/jpeg',
            )
        
        url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
        if url_output is None:
            raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
        image_data = qr_code_cache.add(alias)
        return FileResponse(
            image_data,
            media_type='image/jpeg',
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    status_code_enum = http_code_to_enum[exc.status_code]
    return HTMLResponse(
        content=status_code_enum.content, status_code=status_code_enum.code
    )


@app.get("/metrics")
def get_metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest(),
    )

# write qr-codes to json file on shutdown if cache state file arg is specified
@app.on_event("shutdown")
def signal_handler():
    if args.qr_code_cache_state_file is None:
        return qr_code_cache.clear()
    
    qr_code_cache.write_cache_state()

logging.Formatter.converter = time.gmtime

logging.basicConfig(
    # in mondo we trust
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.ERROR - (args.verbose * 10),
)


def consumer():
    while True:
        alias = alias_queue.get()
        if alias is None:
            break
        try:
            with MetricsHandler.query_time.labels("increment_used").time():
                increment_used_column(DATABASE_FILE, alias)
        except Exception:
            logging.exception("Error updating used count for alias {alias}")
        finally:
            alias_queue.task_done()


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
    MetricsHandler.init()
    MetricsHandler.url_count.inc(initial_url_count)
    consumer_thread = Thread(target=consumer, daemon=True)
    consumer_thread.start()

if __name__ == "__main__":
    logging.info(f"running on {args.host}, listening on port {args.port}")
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)
