import sqlite3
import json
from pathlib import Path

conn = sqlite3.connect('C:/Users/Administrator/.jarvis/memory/chroma.sqlite3')
cursor = conn.cursor()

# 查询 embedding_metadata 并保存到文件
print("正在查询数据库...")

cursor.execute('SELECT * FROM embedding_metadata')
rows = cursor.fetchall()

# 创建输出文件
output_file = Path('./memory_export.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=== JARVIS 长期记忆数据库导出 ===\n\n")
    f.write(f"总记录数: {len(rows)}\n\n")
    f.write("=" * 80 + "\n\n")
    
    for row in rows:
        f.write(f"ID: {row[0]}\n")
        f.write(f"Key: {row[1]}\n")
        f.write(f"Value: {row[2]}\n\n")
        
        # 如果是 chroma:document，解析 JSON
        if row[1] == 'chroma:document':
            try:
                doc = json.loads(row[2])
                f.write("  文档内容:\n")
                f.write(f"    时间戳: {doc.get('timestamp', 'N/A')}\n")
                f.write(f"    任务类型: {doc.get('task_type', 'N/A')}\n")
                f.write(f"    用户输入: {doc.get('user_input', 'N/A')}\n")
                f.write(f"    是否成功: {doc.get('success', 'N/A')}\n")
                f.write(f"    使用工具: {doc.get('tools_used', [])}\n")
                f.write(f"    执行时间: {doc.get('execution_time', 'N/A')}秒\n")
                f.write(f"    用户反馈: {doc.get('user_feedback', 'N/A')}\n")
            except:
                f.write("  (JSON 解析失败)\n")
        
        f.write("-" * 80 + "\n\n")

conn.close()
print(f"导出完成，文件保存在: {output_file}")
print(f"共导出 {len(rows)} 条记录")