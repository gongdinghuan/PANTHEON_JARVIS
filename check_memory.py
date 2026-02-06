import sqlite3
import json

conn = sqlite3.connect('C:/Users/Administrator/.jarvis/memory/chroma.sqlite3')
cursor = conn.cursor()

# 查看embeddings表结构
print("=== Embeddings 表结构 ===")
cursor.execute('PRAGMA table_info(embeddings)')
for row in cursor.fetchall():
    print(row)

print("\n=== 查询前10条记录 ===")
cursor.execute('SELECT * FROM embeddings LIMIT 10')
rows = cursor.fetchall()
for row in rows:
    print(row)

print("\n=== 查询collection_metadata ===")
cursor.execute('SELECT * FROM collection_metadata')
for row in cursor.fetchall():
    print(row)

conn.close()