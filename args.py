import argparse
import time


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-file-path",
        required=True,
        help="path to sqlite database file"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="ip address for server to listen on, defaults to 0.0.0.0"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for server to be hosted on, defaults to 8000"
    )
    parser.add_argument(
        "--disable-random-alias",
        action= "store_true",
        help="disable generating randomly hashed aliases"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="increase logging verbosity; can be used multiple times",
    )
    
    return parser.parse_args()
