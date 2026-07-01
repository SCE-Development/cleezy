from datetime import datetime
import logging
import sqlite3
import typing
from zoneinfo import ZoneInfo


ROWS_PER_PAGE = 25

logger = logging.getLogger(__name__)

def maybe_create_table(sqlite_file: str) -> bool:
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

#new paste table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pastes (
        alias TEXT PRIMARY KEY,
        title TEXT,
        content TEXT NOT NULL
    )
""")

    try:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY, 
            url TEXT NOT NULL, 
            alias TEXT NOT NULL, 
            created_at DATETIME NOT NULL,
            used INTEGER DEFAULT 1,
            expires_at DATETIME DEFAULT NULL);
        """
        create_pastes_table_query = """
        CREATE TABLE IF NOT EXISTS pastes (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_DATE,
            deleted_at DATETIME DEFAULT NULL,
            expires_at DATETIME DEFAULT NULL);
        """
        create_index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_alias
        ON urls (alias);
        """
        cursor.execute(create_pastes_table_query)
        cursor.execute(create_table_query)
        cursor.execute(create_index_query)
        db.commit()
        return True
    except Exception:
        logger.exception("Unable to create urls table")
        return False


def insert_url(sqlite_file: str, url: str, alias: str, expiration_date: typing.Union[str, None] = None):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    timestamp = datetime.now()
    if expiration_date is not None:
        if isinstance(expiration_date, str) and expiration_date.endswith('Z'):
            expiration_date = expiration_date[:-1] + '+00:00'
        expiration_date = datetime.fromisoformat(expiration_date)
    try:
        sql = "INSERT INTO urls(url, alias, created_at, expires_at) VALUES (?, ?, ?, ?)"
        val = (url, alias, timestamp, expiration_date)
        cursor.execute(sql, val)
        db.commit()
        return timestamp
    except sqlite3.IntegrityError:
        return None
    except Exception:
        logger.exception("Inserting url had an error")
        return None

def get_urls(sqlite_file, page=0, search=None, sort_by="created_at", order="DESC"):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    offset = page * ROWS_PER_PAGE
    if search:
        sql = f"""
        SELECT * FROM urls 
        WHERE LOWER(alias) LIKE LOWER('%{search}%') 
        OR LOWER(url) LIKE LOWER('%{search}%')
        ORDER BY {sort_by} {order}
        LIMIT {ROWS_PER_PAGE} OFFSET {offset}
        """
    else:
        sql = f"SELECT * FROM urls ORDER BY {sort_by} {order} LIMIT {ROWS_PER_PAGE} OFFSET {offset}"
    cursor.execute(sql)
    
    result = cursor.fetchall()
    url_array = []
    for row in result:
        try:
            url_data = {
                "id": row[0],
                "url": row[1],
                "alias": row[2],
                "created_at": row[3],
                "used": row[4],
                "expires_at": row[5]
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
    utc_tz = ZoneInfo('UTC')

    expiration_datetime = None
    # sqlite_row[5] represents the expiration datetime in UTC timezone e.g., "2024-11-04 05:09:00+00:00"
    # The following date and datetime formats are now supported:
    # 2024-11-04
    # 2024-11-04T18:05:24
    # 2024-11-04T18:05:24.123456
    # 2024-11-04T18:05:24+02:00
    if sqlite_row[5] is not None:
        expiration_datetime = datetime.fromisoformat(sqlite_row[5])
        expiration_datetime = expiration_datetime.replace(tzinfo=utc_tz)

    now = datetime.now(tz=utc_tz)
    if expiration_datetime is not None and expiration_datetime < now:
        sql = "DELETE FROM urls WHERE alias = ?"
        cursor.execute(sql, (sqlite_row[2], ))
        db.commit()
        return True
    else:
        return False
    
def get_number_of_entries(sqlite_file, search=None):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    count = 0
    try:
        if search:
            sql = f"""
            SELECT COUNT(*) FROM urls 
            WHERE LOWER(alias) LIKE LOWER('%{search}%') 
            OR LOWER(url) LIKE LOWER('%{search}%')
            """
        else:
            sql = "SELECT COUNT(*) FROM urls"

        cursor.execute(sql)
        result = cursor.fetchone()
        count = result[0]
    except Exception as e:
        logger.exception("Couldn't get number of urls: " + str(e))
    finally:
        cursor.close()
        db.close()
    return count

def increment_used_column(sqlite_file, alias: str, count=1):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    try:
        sql = "UPDATE urls SET used = used + ? WHERE alias = ?"
        logging.debug(f"incrementing the used column alias {alias} by {count}")
        cursor.execute(sql, (count, alias))
        db.commit()
    except Exception:
        logger.exception(f"Couldn't update the used column for alias {alias}: ")
        db.rollback()
    finally:
        cursor.close()
        db.close()
