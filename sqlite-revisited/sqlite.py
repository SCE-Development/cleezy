import sqlite3

connection = sqlite3.connect("pastes.db")
cursor = connection.cursor()

cursor.execute("SELECT * FROM pastes")

rows = cursor.fetchall()

print(rows)

connection.close()
