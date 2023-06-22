import argparse
import logging

logging.basicConfig(
    format="%(asctime)s.%(msecs)03dZ %(levelname)s:%(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.DEBUG,
)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db-file-path",
        type=str,
        required=True,
        help="path to sqlite database file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="ip address for server to listen on, defaults to 0.0.0.0"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for server to be hosted on, defaults to 8000"
    )
    
    
    return parser.parse_args()


# --db-file-path
if __name__ == "__main__":
    args = get_args()
    print(args.db_file_path)
    port = 8000
    logging.info(f"starting server on port {port}")
    logging.warning("lil")
    logging.error("uzi")
    logging.debug("vert")
    
"""
import uvicorn


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

