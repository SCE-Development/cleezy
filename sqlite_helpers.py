import sqlite3
import random
import string
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime, timedelta

def maybe_create_table(sqlite_file: str) -> bool:
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()

    try :
        createTableQuery = "CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT, alias TEXT, timestamp DATETIME)"
        cursor.execute(createTableQuery)
        db.commit()
        return True
    except Exception:
        return False
    
def insert_url(sqlite_file: str, url: str, alias: str):
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    timestamp = datetime.now()

    try:
        sql = "INSERT INTO urls(url, alias, timestamp) VALUES (?, ?, ?)"
        val = (url, alias, timestamp)
        cursor.execute(sql, val)
        db.commit()
    except Exception:
        return False

def check_alias_exists(sqlite_file: str, alias: str): #returns True if the alias already exists
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    try:
        sql = "SELECT alias FROM urls WHERE alias = ?"
        cursor.execute(sql, (alias,))
        result = cursor.fetchone()

        if result is not None:
            return True
        else:
            return False
    except Exception:
        return False

def get_urls(sqlite_file: str): #returns all urls in the table
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    
    sql = "SELECT * FROM urls"
    cursor.execute(sql)
    result = cursor.fetchall()
    url_array = []
    for row in result:
        try:
            url_data = {
                "id": row[0],
                "url": row[1],
                "alias": row[2],
                "timestamp": row[3]
            }
            url_array.append(url_data)
        except KeyError:
            continue
    return url_array

def get_url(sqlite_file: str, alias: str): #return the string for url entry for a specified alias
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    result = None
    
    try:
        sql = "SELECT * FROM urls WHERE alias = ?"
        cursor.execute(sql, (alias,))
        result = cursor.fetchone()

        #delete the entry if it has been stored for over a year
        yearAgo = datetime.now() - timedelta(days=365)
        if result[3] < yearAgo:
            sql = "DELETE FROM urls WHERE alias = ?"
            val = alias
            cursor.execute(sql, (val, ))
            db.commit()
            result = None  
        return result[1]
    except Exception:
        return None
    
def delete_url(sqlite_file: str, alias: str): #delete entry in the database from specified alias
    db = sqlite3.connect(sqlite_file)
    cursor = db.cursor()
    result = None

    try:
        sql = "DELETE FROM urls WHERE alias = ?"
        cursor.execute(sql, (alias, ))
        db.commit()

        if cursor.rowcount == 0:
            return False
        else:
            return True
    except Exception:
        return False