#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C盘报告归档脚本
搜索C盘下所有分析报告并归档到PANTHEON_JARVIS/reports文件夹
"""

import os
import shutil
import glob
from datetime import datetime
from pathlib import Path

# 配置
PANTHEON_ROOT = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS"
REPORTS_DIR = os.path.join(PANTHEON_ROOT, "reports")
C_DRIVE = "C:\\"

# 支持的报告类型
REPORT_PATTERNS = [
    "*分析报告*.html",
    "*Analysis*.html",
    "*报告*.html",
    "*Report*.html",
    "*_20*.html",  # 包含日期的报告
]

# 需要跳过的目录
SKIP_DIRS = [
    "Windows",
    "System Volume Information",
    "$Recycle.Bin",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "AppData",
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
]

def should_skip_dir(dirname):
    """判断是否应该跳过该目录"""
    for skip in SKIP_DIRS:
        if skip.lower() in dirname.lower():
            return True
    return False

def find_reports_in_c_drive():
    """在C盘搜索所有报告文件"""
    print("[INFO] 开始搜索C盘下的所有分析报告...")
    print("=" * 60)
    
    found_reports = []
    searched_dirs = 0
    
    # 只搜索用户目录和常见的项目目录
    search_paths = [
        os.path.join(C_DRIVE, "Users"),
        os.path.join(C_DRIVE, "Users\\Administrator\\Desktop"),
        os.path.join(C_DRIVE, "Users\\Administrator\\Documents"),
        os.path.join(C_DRIVE, "Users\\Administrator\\Downloads"),
    ]
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
            
        print(f"[SEARCH] 扫描路径: {base_path}")
        
        for root, dirs, files in os.walk(base_path):
            # 过滤掉需要跳过的目录
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]
            
            searched_dirs += 1
            
            # 检查该目录下是否有报告文件
            for pattern in REPORT_PATTERNS:
                for file in glob.glob(os.path.join(root, pattern)):
                    # 跳过已经在reports文件夹中的文件
                    if "PANTHEON_JARVIS\\reports" in file:
                        continue
                    
                    file_path = os.path.abspath(file)
                    if file_path not in found_reports:
                        found_reports.append(file_path)
                        print(f"  [FOUND] 找到报告: {os.path.basename(file)}")
    
    print("=" * 60)
    print(f"[SUCCESS] 搜索完成！共找到 {len(found_reports)} 个报告文件")
    print(f"[INFO] 扫描了 {searched_dirs} 个目录")
    
    return found_reports

def archive_report(src_path, reports_dir):
    """归档单个报告文件"""
    filename = os.path.basename(src_path)
    dest_path = os.path.join(reports_dir, filename)
    
    # 如果目标文件已存在，添加时间戳
    if os.path.exists(dest_path):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{name}_{timestamp}{ext}"
        dest_path = os.path.join(reports_dir, new_filename)
    
    try:
        shutil.copy2(src_path, dest_path)
        print(f"  [SUCCESS] 归档成功: {filename}")
        return True, filename
    except Exception as e:
        print(f"  [ERROR] 归档失败: {filename} - {str(e)}")
        return False, filename

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("[START] C盘报告归档脚本启动")
    print(f"[TIME] 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    # 确保reports目录存在
    os.makedirs(REPORTS_DIR, exist_ok=True)
    print(f"[INFO] 目标归档目录: {REPORTS_DIR}\n")
    
    # 搜索C盘下的所有报告
    found_reports = find_reports_in_c_drive()
    
    if not found_reports:
        print("\n[INFO] 没有找到需要归档的报告文件")
        return
    
    # 归档报告
    print("\n" + "=" * 60)
    print("[ARCHIVE] 开始归档报告文件...")
    print("=" * 60 + "\n")
    
    archived_count = 0
    failed_count = 0
    
    for report_path in found_reports:
        success, filename = archive_report(report_path, REPORTS_DIR)
        if success:
            archived_count += 1
        else:
            failed_count += 1
    
    # 输出总结
    print("\n" + "=" * 60)
    print("[COMPLETE] 归档完成！")
    print("=" * 60)
    print(f"[SUCCESS] 成功归档: {archived_count} 个文件")
    print(f"[FAILED] 归档失败: {failed_count} 个文件")
    print(f"[PATH] 归档目录: {REPORTS_DIR}")
    print(f"[URL] 在线访问: http://43.135.129.25:8765/reports/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
