import sqlite3
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)

def maybe_create_table(sqlite_file: str) -> bool:
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    try :
        create_table_query = """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY, 
            url TEXT NOT NULL, 
            alias TEXT NOT NULL, 
            created_at DATETIME NOT NULL);
        """

        create_index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_alias
        ON urls (alias);
        """

        cursor.execute(create_table_query)
        cursor.execute(create_index_query)
        db.commit()
        return True
    except Exception:
        logger.exception("Unable to create urls table")
        return False

def insert_url(sqlite_file: str, url: str, alias: str):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    timestamp = datetime.now()

    try:
        sql = "INSERT INTO urls(url, alias, created_at) VALUES (?, ?, ?)"
        val = (url, alias, timestamp)
        cursor.execute(sql, val)
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        logger.exception("Inserting url had an error")
        return False

def get_urls(sqlite_file, page, limit):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    offset = (page - 1) * limit
    sql = "SELECT * FROM urls LIMIT ? OFFSET ?"
    cursor.execute(sql, (limit, offset))
    result = cursor.fetchall()
    url_array = []
    for row in result:
        url_data = {
                "id": row[0],
                "url": row[1],
                "alias": row[2],
                "created_at": row[3]
            }
        url_array.append(url_data)
    return url_array

def search(sqlite_file, search_term, page, limit):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    offset = (page - 1) * limit
    sql = """
    SELECT * FROM urls 
    WHERE LOWER(alias) LIKE LOWER(?) 
    OR LOWER(url) LIKE LOWER(?)
    LIMIT ? OFFSET ?
    """
    cursor.execute(sql, ('%' + search_term + '%', '%' + search_term + '%', limit, offset))
    result = cursor.fetchall()
    url_array = []
    for row in result:
        url_data = {
            "alias": row[2],
            "url": row[1]
        }
        url_array.append(url_data)
    return url_array

def delete_url(sqlite_file: str, alias: str): #delete entry in the database from specified alias
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    try:
        sql = "DELETE FROM urls WHERE alias = ?"
        cursor.execute(sql, (alias, ))
        db.commit()

        return cursor.rowcount > 0
    except Exception:
        logger.exception("Deleting url had an error")
        return False
    
def maybe_delete_expired_url(sqlite_file, sqlite_row) -> bool: #returns True if url expired and deleted, otherwise False
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    year_ago_date = datetime.now() - timedelta(days=365)
    result_datetime_str = sqlite_row[3].split(".")[0]  # Remove fractional seconds
    result_datetime = datetime.strptime(result_datetime_str, "%Y-%m-%d %H:%M:%S")
    if result_datetime < year_ago_date:
        sql = "DELETE FROM urls WHERE alias = ?"
        cursor.execute(sql, (sqlite_row[2], ))
        db.commit()
        return True
    else:
        return False
    
def get_number_of_entries(sqlite_file):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    count = 0
    try:
        sql = "SELECT COUNT(*) FROM urls"
        cursor.execute(sql)
        result = cursor.fetchone()
        count = result[0]
    except Exception:
        logger.exception("Couldn't get number of urls")
    return count