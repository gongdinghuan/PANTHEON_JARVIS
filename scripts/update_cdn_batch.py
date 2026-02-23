#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS CDN批量更新脚本
功能：批量更新历史HTML报告的ECharts CDN配置
作者：JARVIS
日期：2026-02-11
"""

import os
import re
import sys
from datetime import datetime

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ==================== 配置区 ====================

# 报告目录
REPORTS_DIR = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports"

# CDN替换映射表（正则表达式 -> 新CDN URL）
CDN_REPLACEMENTS = {
    # ECharts CDN映射
    r'https://cdn\.jsdelivr\.net/npm/echarts[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/echarts[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js',
    r'https://unpkg\.com/echarts[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js',
    r'echarts\.(min\.)?js[^"\']*': 'https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js',
    
    # Chart.js CDN映射
    r'https://cdn\.jsdelivr\.net/npm/chart\.js[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/Chart\.js[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
    
    # jQuery CDN映射
    r'https://cdn\.jsdelivr\.net/npm/jquery[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/jquery/3.7.1/jquery.min.js',
    r'https://cdnjs\.cloudflare\.com/ajax/libs/jquery[^"\']*\.js': 'https://cdn.bootcdn.net/ajax/libs/jquery/3.7.1/jquery.min.js',
}

# ==================== 主程序 ====================

def update_cdn_in_file(filepath):
    """更新单个文件的CDN配置"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # 检查是否包含常见图表库
        if not any(lib in content.lower() for lib in ['echarts', 'chart.js', 'chartjs']):
            return {'status': 'skip', 'reason': '不包含图表库'}
        
        # 应用替换规则
        for pattern, replacement in CDN_REPLACEMENTS.items():
            new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            if new_content != content:
                updated = True
                content = new_content
        
        # 如果内容有变化，写回文件
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return {'status': 'updated'}
        else:
            return {'status': 'skip', 'reason': '已是国内CDN'}
            
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def batch_update_cdn():
    """批量更新CDN配置"""
    print("=" * 70)
    print("[INFO] JARVIS CDN Batch Update Tool")
    print("=" * 70)
    print(f"[DIR] Reports Directory: {REPORTS_DIR}")
    print(f"[TIME] Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 统计信息
    stats = {
        'total': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'updated_files': [],
        'error_files': []
    }
    
    # 遍历所有HTML文件
    html_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.html')]
    stats['total'] = len(html_files)
    
    print(f"[SCAN] Found {stats['total']} HTML files")
    print("-" * 70)
    
    # 处理每个文件
    for i, filename in enumerate(html_files, 1):
        filepath = os.path.join(REPORTS_DIR, filename)
        result = update_cdn_in_file(filepath)
        
        # 显示进度
        progress = f"[{i}/{stats['total']}]"
        
        if result['status'] == 'updated':
            stats['updated'] += 1
            stats['updated_files'].append(filename)
            print(f"[OK] {progress} {filename}")
            
        elif result['status'] == 'skip':
            stats['skipped'] += 1
            reason = result.get('reason', 'Unknown')
            print(f"[SKIP] {progress} {filename} ({reason})")
            
        elif result['status'] == 'error':
            stats['errors'] += 1
            stats['error_files'].append((filename, result['error']))
            print(f"[ERROR] {progress} {filename} - {result['error']}")
    
    # 输出统计结果
    print()
    print("=" * 70)
    print("[STATS] Update Statistics")
    print("=" * 70)
    print(f"Total Files:     {stats['total']}")
    print(f"Updated:         {stats['updated']}")
    print(f"Skipped:         {stats['skipped']}")
    print(f"Errors:          {stats['errors']}")
    print(f"End Time:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 显示更新列表（最多30个）
    if stats['updated_files']:
        print()
        print("[UPDATED] Updated Files (first 30):")
        for i, filename in enumerate(stats['updated_files'][:30], 1):
            print(f"   {i}. {filename}")
        if len(stats['updated_files']) > 30:
            print(f"   ... and {len(stats['updated_files']) - 30} more files")
    
    # 显示错误列表
    if stats['error_files']:
        print()
        print("[ERRORS] Error Files:")
        for filename, error in stats['error_files']:
            print(f"   - {filename}: {error}")
    
    print()
    print("=" * 70)
    print("[SUCCESS] Batch Update Complete!")
    print("=" * 70)
    
    return stats

if __name__ == "__main__":
    batch_update_cdn()
