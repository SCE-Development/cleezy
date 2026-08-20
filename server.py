from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse, PlainTextResponse
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

from pathlib import Path
import os

CLEEZY_PASTE_API_KEY = os.getenv("CLEEZY_PASTE_API_KEY")

MAX_PASTE_SIZE_BYTES = 10 * 1024 * 1024

app = FastAPI()
args = get_args()

PASTES_DIR = Path(args.paste_directory)
PASTES_DIR.mkdir(exist_ok=True)

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


@app.post("/url/create")
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
        expiration_date = urljson.get("expires_at")

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


@app.get("/url/list")
async def get_urls(
    search: Optional[str] = None,
    page: int = 0,
    sort_by: str = "created_at",
    order: str = "DESC",
):
    valid_sort_attributes = {"id", "url", "alias", "created_at", "expires_at", "used"}
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


@app.get("/url/find/{alias}")
async def get_url(alias: str):
    logging.debug(f"/find called with alias: {alias}")
    url_output = cache.find(alias)  # try to find url in cache
    if url_output is not None:
        valid = sqlite_helpers.get_url(DATABASE_FILE, alias)
        if valid is None:
            cache.delete(alias)
            raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
        alias_queue.put(alias)
        return RedirectResponse(url_output)

    with MetricsHandler.query_time.labels("find").time():
        url_output = sqlite_helpers.get_url(DATABASE_FILE, alias)
    if url_output is None:
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    cache.add(alias, url_output)  # else, adds url and alias to cache

    alias_queue.put(alias)
    return RedirectResponse(url_output)


@app.post("/url/delete/{alias}")
async def delete_url(alias: str):
    logging.debug(f"/delete called with alias: {alias}")
    with MetricsHandler.query_time.labels("delete").time():
        if sqlite_helpers.delete_url(DATABASE_FILE, alias):
            qr_code_cache.delete(alias)
            cache.delete(alias)
            return {"message": "URL deleted successfully"}
        else:
            raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)

@app.post("/paste/create")
async def create_paste(request: Request):
    api_key = request.headers.get("x-api-key")

    if CLEEZY_PASTE_API_KEY is None:
        logging.warning("CLEEZY_PASTE_API_KEY isn't set, skipping api key check")
    elif api_key != CLEEZY_PASTE_API_KEY:
        raise HTTPException(status_code=401, detail=f"Invalid API Key '{api_key}'")

    try:
        payload = await request.json()
    except Exception:
        logging.exception("/paste/create couldnt parse json")
        raise HTTPException(
            status_code=HttpResponse.BAD_REQUEST.code,
            detail="Invalid JSON payload"
        )
    text_bytes = payload.get("text", "").encode("utf-8")
    if len(text_bytes) > MAX_PASTE_SIZE_BYTES:
        raise HTTPException(
            status_code=HttpResponse.REQUEST_TOO_LARGE,
            detail="Paste content exceeds the maximum allowed size of 10MB."
        )

    paste_id = generate_alias(len(payload.get('text')))

    success = sqlite_helpers.insert_paste(DATABASE_FILE, paste_id, payload.get('title', 'Untitled Paste'))
    if not success:
        raise HTTPException(
            status_code=HttpResponse.INTERNAL_SERVER_ERROR,
            detail="Failed to save paste metadata."
        )

    paste_path = PASTES_DIR / str(paste_id)
    paste_path.write_bytes(text_bytes)

    return {
        "status": "success",
        "id": paste_id,
        "url": f"/paste/{paste_id}"
    }


@app.get("/paste/{paste_id}")
async def view_paste(paste_id: str):
    paste_path = PASTES_DIR / paste_id
    if not paste_path.exists():
        raise HTTPException(status_code=HttpResponse.NOT_FOUND.code)
    return PlainTextResponse(paste_path.read_text(encoding="utf-8"))

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
    content = status_code_enum.content
    if status_code_enum == HttpResponse.NOT_FOUND:
        original_url = request.headers.get("x-original-url", request.url)
        base_url = request.headers.get("x-base-url", request.base_url)
        content = content.format(
            requested_url=str(original_url),
            base_url=str(base_url)
        )
    if status_code_enum == HttpResponse.REQUEST_TOO_LARGE:
        request_size = "Unknown"
        try:
            body = await request.json()
            if isinstance(body, dict) and "text" in body:
                request_size = len(body["text"].encode("utf-8"))
        except Exception:
            pass
        content = content.format(
            request_size=request_size,
            max_size=MAX_PASTE_SIZE_BYTES,
        )
    return HTMLResponse(
        content=content, status_code=status_code_enum.code
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
