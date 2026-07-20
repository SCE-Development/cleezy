from fastapi import FastAPI
import sqlite3
import uuid

app = FastAPI()
DATABASE = "pastes.db"

def database_setup():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS pastes (name TEXT, filename TEXT)""")
    
    connection.commit()
    connection.close()

database_setup()

@app.get("/paste/list")
def pastes_list():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM pastes")
    rows = cursor.fetchall()

    connection.close()

    return rows

@app.post("/paste/create")
def create_paste(data: dict):
    name = data["name"]
    content = data["content"]

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    
    filename = str(uuid.uuid4()) + ".txt"

    with open(filename, "w") as file:
        file.write(content)

    cursor.execute("INSERT INTO pastes (name, filename) VALUES (?, ?)",
    (name, filename)
)

    connection.commit()
    connection.close()
	
    return {"name": name, "content": content}

@app.get("/paste/view/{name}")
def check_paste_exist(name: str):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("SELECT filename FROM pastes WHERE name = ?",
    (name,)
)
    paste = cursor.fetchone()
    
    connection.close()
 
    if paste: 
        filename = paste[0]
        
        with open(filename, "r") as file:
            content = file.read()

        return content

    return "no!"

