#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动更新报告索引脚本
功能：扫描reports文件夹，生成/更新index.html
"""

import os
import sys
import json
import glob
from datetime import datetime
from pathlib import Path

# 设置控制台输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
REPORTS_DIR = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports"
INDEX_FILE = os.path.join(REPORTS_DIR, "index.html")
LOG_FILE = os.path.join(REPORTS_DIR, "index_update.log")

# 报告分类关键词
CATEGORIES = {
    "金融分析": ["股票", "估值", "财务", "投资", "交易", "持仓", "portfolio", "financial", "analysis", "valuation"],
    "技术报告": ["技术", "芯片", "良率", "18A", "工艺", "tech", "yield", "process"],
    "市场研究": ["市场", "行业", "竞争", "market", "industry", "competition"],
    "AI分析": ["AI", "人工智能", "机器学习", "深度学习", "AGI", "智能", "embodied"],
    "咨询报告": ["咨询", "Daily", "brief", "报告"],
    "学习资料": ["学习", "指南", "tutorial", "guide", "learning", "HTML", "ECharts"]
}

def classify_report(filename):
    """根据文件名分类报告"""
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in filename.lower():
                return category
    return "其他"

def get_file_info(filepath):
    """获取文件信息"""
    try:
        stat = os.stat(filepath)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        size = stat.st_size
        
        # 提取日期
        filename = os.path.basename(filepath)
        date_str = mtime.strftime("%Y-%m-%d")
        
        # 分类
        category = classify_report(filename)
        
        # 文件类型
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.html':
            file_type = "HTML"
        elif ext == '.md':
            file_type = "Markdown"
        elif ext == '.json':
            file_type = "JSON"
        else:
            file_type = "其他"
        
        return {
            "name": filename,
            "path": f"./{filename}",
            "size": size,
            "date": date_str,
            "category": category,
            "type": file_type
        }
    except Exception as e:
        print(f"[ERROR] 获取文件信息失败: {filepath}, 错误: {e}")
        return None

def scan_reports():
    """扫描所有报告文件"""
    print("[INFO] 开始扫描报告文件夹...")
    
    # 支持的文件类型
    extensions = ['*.html', '*.htm', '*.md', '*.json']
    
    files = []
    for ext in extensions:
        pattern = os.path.join(REPORTS_DIR, ext)
        files.extend(glob.glob(pattern))
    
    # 排除index.html自身
    files = [f for f in files if os.path.basename(f) != 'index.html']
    
    # 获取文件信息
    reports = []
    for filepath in files:
        info = get_file_info(filepath)
        if info:
            reports.append(info)
    
    # 按日期排序（最新的在前）
    reports.sort(key=lambda x: x['date'], reverse=True)
    
    print(f"[SUCCESS] 扫描完成，找到 {len(reports)} 个报告文件")
    return reports

def generate_index_html(reports):
    """生成索引HTML"""
    print("[INFO] 生成索引HTML...")
    
    # 统计数据
    total = len(reports)
    html_count = sum(1 for r in reports if r['type'] == 'HTML')
    md_count = sum(1 for r in reports if r['type'] == 'Markdown')
    json_count = sum(1 for r in reports if r['type'] == 'JSON')
    
    # 分类统计
    category_stats = {}
    for r in reports:
        cat = r['category']
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    # 生成报告卡片HTML
    cards_html = ""
    for r in reports:
        # 颜色映射
        color_map = {
            "金融分析": "#00d4aa",
            "技术报告": "#00d4ff",
            "市场研究": "#ff9f43",
            "AI分析": "#a55eea",
            "咨询报告": "#ff6b6b",
            "学习资料": "#45aaf2",
            "其他": "#778ca3"
        }
        color = color_map.get(r['category'], '#778ca3')
        
        cards_html += f'''
        <div class="report-card" data-category="{r['category']}" data-date="{r['date']}">
            <div class="card-header">
                <span class="category-tag" style="background: {color}20; color: {color}; border-left: 3px solid {color};">
                    {r['category']}
                </span>
                <span class="file-type">{r['type']}</span>
            </div>
            <div class="card-body">
                <h3 class="report-title">{r['name']}</h3>
                <div class="report-meta">
                    <span class="date">📅 {r['date']}</span>
                    <span class="size">📦 {r['size'] / 1024:.1f} KB</span>
                </div>
            </div>
            <div class="card-footer">
                <a href="{r['path']}" target="_blank" class="btn-view">📊 查看报告</a>
            </div>
        </div>
        '''
    
    # 生成分类选项
    categories_html = '<option value="all">📋 全部分类</option>'
    for cat in sorted(category_stats.keys()):
        count = category_stats[cat]
        categories_html += f'<option value="{cat}">{cat} ({count})</option>'
    
    # 生成ECharts数据
    category_data_json = json.dumps(category_stats, ensure_ascii=False)
    
    # 完整HTML模板
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS 报告索引 | {total}份报告</title>
    <script src="https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        /* 头部样式 */
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(0,212,255,0.1) 0%, rgba(165,94,234,0.1) 100%);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00d4ff, #a55eea);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header p {{ color: #888; font-size: 1.1em; }}
        
        /* 统计卡片 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
            transition: all 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.2);
        }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .stat-label {{ color: #888; font-size: 0.9em; }}
        
        /* 图表容器 */
        .chart-container {{
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 40px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        #categoryChart {{ height: 350px; }}
        
        /* 控制面板 */
        .controls {{
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .controls input, .controls select {{
            flex: 1;
            min-width: 200px;
            padding: 12px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #fff;
            font-size: 1em;
        }}
        .controls input:focus, .controls select:focus {{
            outline: none;
            border-color: #00d4ff;
        }}
        
        /* 报告网格 */
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 25px;
        }}
        
        /* 报告卡片 */
        .report-card {{
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }}
        .report-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(0,212,255,0.3);
            border-color: rgba(0,212,255,0.5);
        }}
        .card-header {{
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.03);
        }}
        .category-tag {{
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .file-type {{
            font-size: 0.8em;
            color: #888;
            padding: 3px 8px;
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
        }}
        .card-body {{ padding: 20px; }}
        .report-title {{
            font-size: 1.1em;
            margin-bottom: 15px;
            color: #fff;
            line-height: 1.4;
            word-break: break-all;
        }}
        .report-meta {{
            display: flex;
            justify-content: space-between;
            color: #888;
            font-size: 0.9em;
        }}
        .card-footer {{ padding: 15px; }}
        .btn-view {{
            display: block;
            text-align: center;
            padding: 12px;
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            color: #fff;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .btn-view:hover {{
            background: linear-gradient(135deg, #0099cc 0%, #00d4ff 100%);
            transform: scale(1.02);
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            color: #888;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        
        /* 更新时间 */
        .update-time {{
            text-align: center;
            margin-top: 20px;
            color: #00d4ff;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8em; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .reports-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>JARVIS 报告索引中心</h1>
            <p>J.A.R.V.I.S. Analysis Reports Archive | {total}份专业报告</p>
            <p style="margin-top: 10px; font-size: 0.9em; color: #00d4ff;">
                最后更新: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </div>
        
        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" style="color: #00d4ff;">{total}</div>
                <div class="stat-label">总报告数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #00d4aa;">{html_count}</div>
                <div class="stat-label">HTML报告</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #ff9f43;">{md_count}</div>
                <div class="stat-label">Markdown</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #a55eea;">{json_count}</div>
                <div class="stat-label">JSON数据</div>
            </div>
        </div>
        
        <!-- 图表 -->
        <div class="chart-container">
            <h2 style="text-align: center; margin-bottom: 20px;">报告分类分布</h2>
            <div id="categoryChart"></div>
        </div>
        
        <!-- 控制面板 -->
        <div class="controls">
            <input type="text" id="searchInput" placeholder="搜索报告名称、关键词...">
            <select id="categoryFilter">
                {categories_html}
            </select>
            <select id="sortFilter">
                <option value="newest">最新优先</option>
                <option value="oldest">最旧优先</option>
                <option value="name">名称排序</option>
                <option value="size">大小排序</option>
            </select>
        </div>
        
        <!-- 报告网格 -->
        <div class="reports-grid" id="reportsGrid">
            {cards_html}
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>Powered by J.A.R.V.I.S. | Just A Rather Very Intelligent System</p>
            <p style="margin-top: 10px;">存储位置: {REPORTS_DIR}</p>
            <div class="update-time">
                自动更新: 每天凌晨 03:00
            </div>
        </div>
    </div>
    
    <script>
        // ECharts图表
        const chartDom = document.getElementById('categoryChart');
        const myChart = echarts.init(chartDom);
        
        const categoryData = {category_data_json};
        
        const option = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'item',
                formatter: '{{b}}: {{c}} 份 ({{d}}%)'
            }},
            legend: {{
                orient: 'vertical',
                right: 20,
                top: 'center',
                textStyle: {{ color: '#fff' }}
            }},
            series: [{{
                name: '报告分类',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['40%', '50%'],
                data: Object.keys(categoryData).map(key => ({{
                    value: categoryData[key],
                    name: key
                }})),
                emphasis: {{
                    itemStyle: {{
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 212, 255, 0.5)'
                    }}
                }},
                label: {{
                    color: '#fff'
                }}
            }}]
        }};
        
        myChart.setOption(option);
        window.addEventListener('resize', () => myChart.resize());
        
        // 搜索和过滤功能
        const searchInput = document.getElementById('searchInput');
        const categoryFilter = document.getElementById('categoryFilter');
        const sortFilter = document.getElementById('sortFilter');
        const reportsGrid = document.getElementById('reportsGrid');
        const cards = document.querySelectorAll('.report-card');
        
        function filterReports() {{
            const searchTerm = searchInput.value.toLowerCase();
            const category = categoryFilter.value;
            const sort = sortFilter.value;
            
            let visibleCards = [];
            
            cards.forEach(card => {{
                const title = card.querySelector('.report-title').textContent.toLowerCase();
                const cardCategory = card.dataset.category;
                const cardDate = card.dataset.date;
                
                // 匹配搜索词和分类
                const matchesSearch = title.includes(searchTerm);
                const matchesCategory = category === 'all' || cardCategory === category;
                
                if (matchesSearch && matchesCategory) {{
                    card.style.display = 'block';
                    visibleCards.push(card);
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            
            // 排序
            visibleCards.sort((a, b) => {{
                if (sort === 'newest') return b.dataset.date.localeCompare(a.dataset.date);
                if (sort === 'oldest') return a.dataset.date.localeCompare(b.dataset.date);
                if (sort === 'name') return a.querySelector('.report-title').textContent.localeCompare(b.querySelector('.report-title').textContent);
                if (sort === 'size') return parseInt(b.querySelector('.size').textContent) - parseInt(a.querySelector('.size').textContent);
            }});
            
            // 重新排序DOM
            visibleCards.forEach(card => reportsGrid.appendChild(card));
        }}
        
        searchInput.addEventListener('input', filterReports);
        categoryFilter.addEventListener('change', filterReports);
        sortFilter.addEventListener('change', filterReports);
    </script>
</body>
</html>'''
    
    return html_template

def save_log(message):
    """保存日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[ERROR] 保存日志失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("JARVIS 自动更新报告索引")
    print("=" * 60)
    
    try:
        # 扫描报告
        reports = scan_reports()
        
        if not reports:
            print("[WARN] 没有找到报告文件")
            save_log("扫描完成，未找到报告文件")
            return
        
        # 生成HTML
        html_content = generate_index_html(reports)
        
        # 保存文件
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[SUCCESS] 索引已更新: {INDEX_FILE}")
        print(f"[INFO] 总报告数: {len(reports)}")
        save_log(f"索引更新成功，共{len(reports)}份报告")
        
    except Exception as e:
        print(f"[ERROR] 更新失败: {e}")
        save_log(f"更新失败: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
