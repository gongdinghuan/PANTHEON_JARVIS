import sqlite3

conn = sqlite3.connect('C:/Users/Administrator/.jarvis/memory/chroma.sqlite3')
cursor = conn.cursor()

print("=== 查询 segment_metadata ===")
cursor.execute('SELECT * FROM segment_metadata')
for row in cursor.fetchall():
    print(row)

print("\n=== 查询 embedding_metadata ===")
cursor.execute('SELECT * FROM embedding_metadata')
for row in cursor.fetchall():
    print(row)

print("\n=== 查询 segments ===")
cursor.execute('SELECT * FROM segments')
for row in cursor.fetchall():
    print(row)

conn.close()