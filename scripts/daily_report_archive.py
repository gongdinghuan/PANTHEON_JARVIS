#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日报告归档脚本
自动将散落的报告文件归档到reports文件夹
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json

# 配置
ROOT_DIR = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS"
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
LOG_FILE = os.path.join(REPORTS_DIR, "archive_log.json")

def load_archive_log():
    """加载归档日志"""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archived_files": []}

def save_archive_log(log):
    """保存归档日志"""
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def is_report_file(filename):
    """判断是否为报告文件"""
    # 排除已归档的文件
    if filename.startswith("__pycache__"):
        return False
    if filename.endswith(".py"):
        return False
    if filename.endswith(".json"):
        return False
    
    # 匹配报告文件特征
    report_patterns = [
        "_Report_",
        "_Analysis_",
        "_20260",
        "Daily_",
        "Big_Tech_",
        "AI_",
        "Microsoft_",
        "Amazon_",
        "OpenAI_",
        "Crypto_",
        "finance_",
        "consulting_",
        "Desktop_",
    ]
    
    return any(pattern in filename for pattern in report_patterns)

def scan_root_directory():
    """扫描根目录下的报告文件"""
    root_path = Path(ROOT_DIR)
    report_files = []
    
    # 扫描根目录下的.html文件
    for file in root_path.glob("*.html"):
        if is_report_file(file.name):
            report_files.append(file)
    
    # 扫描data目录下的.html文件
    data_path = root_path / "data"
    if data_path.exists():
        for file in data_path.glob("**/*.html"):
            if is_report_file(file.name):
                report_files.append(file)
    
    return report_files

def archive_reports():
    """归档报告文件"""
    # 确保reports目录存在
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # 加载归档日志
    log = load_archive_log()
    archived = set(log["archived_files"])
    
    # 扫描报告文件
    report_files = scan_root_directory()
    
    # 归档统计
    moved_files = []
    skipped_files = []
    
    for file in report_files:
        file_path = str(file)
        file_name = file.name
        
        # 跳过已归档的文件
        if file_path in archived:
            skipped_files.append(file_name)
            continue
        
        # 跳过已在reports目录的文件
        if REPORTS_DIR in file_path:
            continue
        
        # 移动文件
        destination = os.path.join(REPORTS_DIR, file_name)
        
        # 如果目标文件已存在，添加时间戳
        if os.path.exists(destination):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_part, ext_part = os.path.splitext(file_name)
            destination = os.path.join(REPORTS_DIR, f"{name_part}_{timestamp}{ext_part}")
        
        try:
            shutil.move(file_path, destination)
            moved_files.append({
                "from": file_path,
                "to": destination,
                "name": file_name,
                "time": datetime.now().isoformat()
            })
            archived.add(file_path)
        except Exception as e:
            print(f"移动失败 {file_name}: {e}")
    
    # 更新归档日志
    log["archived_files"] = list(archived)
    log["last_run"] = datetime.now().isoformat()
    log["last_run_stats"] = {
        "moved": len(moved_files),
        "skipped": len(skipped_files)
    }
    save_archive_log(log)
    
    return {
        "moved": moved_files,
        "skipped": skipped_files,
        "total": len(report_files)
    }

def generate_report(result):
    """生成归档报告"""
    report_lines = [
        f"# 📁 每日报告归档完成报告",
        f"",
        f"**执行时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 📊 归档统计",
        f"",
        f"| 指标 | 数量 |",
        f"|:-----|:-----|",
        f"| **新归档** | {len(result['moved'])} |",
        f"| **已跳过** | {len(result['skipped'])} |",
        f"| **总计扫描** | {result['total']} |",
        f"",
    ]
    
    if result['moved']:
        report_lines.extend([
            f"## ✅ 新归档文件",
            f"",
        ])
        for file in result['moved']:
            report_lines.append(f"- **{file['name']}**")
    
    report_lines.extend([
        f"",
        f"---",
        f"",
        f"**归档位置：** `{REPORTS_DIR}`",
        f"",
        f"**在线访问：** http://43.135.129.25:8765/reports/",
    ])
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    print("📁 开始每日报告归档...")
    result = archive_reports()
    report = generate_report(result)
    print(report)
    print(f"\n✅ 归档完成！新归档 {len(result['moved'])} 个文件")
