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

def get_urls(sqlite_file: str): #returns all urls in the table
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    sql = "SELECT * from urls order by created_at desc"
    cursor.execute(sql)
    result = cursor.fetchall()
    url_array = []
    for row in result:
        try:
            url_data = {
                "id": row[0],
                "url": row[1],
                "alias": row[2],
                "created_at": row[3]
            }
            url_array.append(url_data)
        except KeyError:
            continue
    return url_array

def get_url(sqlite_file: str, alias: str): #return the string for url entry for a specified alias
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    try:
        sql = "SELECT * FROM urls WHERE alias = ?"
        cursor.execute(sql, (alias,))
        result = cursor.fetchone()

        #delete the entry if it has been stored for over a year
        if not result or maybe_delete_expired_url(sqlite_file, result):
            return None
        else:
            return result[1]
    except Exception:
        logger.exception("Getting url had an error")
        return None
    
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
