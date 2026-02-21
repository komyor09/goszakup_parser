from db.database import init_db, get_connection

init_db()

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cur.fetchall())

conn.close()