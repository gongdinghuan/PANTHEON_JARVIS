#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融知识固化与知识图谱更新系统
Memory Consolidation and Knowledge Graph Update System
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class MemoryConsolidationSystem:
    """知识固化与图谱更新系统"""
    
    def __init__(self):
        self.base_path = Path("C:/Users/Administrator/Desktop/workspace/PANTHEON_JARVIS/memory")
        self.knowledge_graph_path = self.base_path / "knowledge_graph"
        self.consolidation_path = self.base_path / "consolidated_memory"
        
        # 创建必要的目录
        self.knowledge_graph_path.mkdir(parents=True, exist_ok=True)
        self.consolidation_path.mkdir(parents=True, exist_ok=True)
        
        # 当前日期
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.now = datetime.now()
    
    def consolidate_daily_learning(self):
        """固化当天的学习内容"""
        print("Starting knowledge consolidation process...")
        
        # 1. 收集当天的学习内容
        learning_content = {
            "date": self.today,
            "timestamp": self.now.isoformat(),
            "learning_sessions": [
                {
                    "session_id": "finance_analysis_20260207",
                    "topic": "金融分析技能深度学习",
                    "duration": "10分钟",
                    "areas": [
                        {
                            "name": "实时数据处理",
                            "technologies": ["Pandas", "NumPy", "Apache Kafka", "WebSocket"],
                            "concepts": [
                                "高频数据流处理架构",
                                "多源数据整合（API、数据库、实时流）",
                                "数据清洗与标准化管道",
                                "异常检测与数据质量控制"
                            ],
                            "mastery_level": "目标85%",
                            "applications": ["实时行情监控", "交易信号生成", "风险预警系统"]
                        },
                        {
                            "name": "技术指标计算",
                            "technologies": ["TA-Lib", "Pandas", "Custom Algorithms"],
                            "indicators": {
                                "趋势指标": ["SMA", "EMA", "MACD"],
                                "动量指标": ["RSI", "Stochastic", "CCI"],
                                "波动率指标": ["布林带", "ATR"],
                                "成交量指标": ["OBV", "VWAP"]
                            },
                            "mastery_level": "目标90%",
                            "applications": ["趋势识别", "入场/出场信号", "市场状态判断"]
                        },
                        {
                            "name": "机器学习预测",
                            "technologies": ["Scikit-learn", "TensorFlow", "PyTorch", "Statsmodels"],
                            "models": {
                                "时间序列": ["LSTM", "GRU", "Prophet"],
                                "回归模型": ["Random Forest", "XGBoost"],
                                "分类算法": ["SVM", "Neural Networks"]
                            },
                            "mastery_level": "目标80%",
                            "applications": ["价格预测", "趋势分类", "异常检测"]
                        },
                        {
                            "name": "风险管理算法",
                            "technologies": ["NumPy", "SciPy", "QuantLib"],
                            "methods": {
                                "VaR计算": ["历史法", "蒙特卡洛", "参数法"],
                                "高级风险": ["CVaR", "压力测试", "情景分析"],
                                "风控策略": ["止损策略", "仓位管理"]
                            },
                            "mastery_level": "目标88%",
                            "applications": ["投资组合风险评估", "极端情况预警", "资金管理"]
                        },
                        {
                            "name": "投资组合优化",
                            "technologies": ["PyPortfolioOpt", "CVXPY", "scipy.optimize"],
                            "models": {
                                "经典模型": ["马科维茨均值-方差", "Black-Litterman"],
                                "现代方法": ["风险平价", "多因子模型"]
                            },
                            "mastery_level": "目标82%",
                            "applications": ["资产配置", "风险分散", "收益优化"]
                        },
                        {
                            "name": "量化交易策略",
                            "technologies": ["Backtrader", "Zipline", "VectorBT"],
                            "strategies": {
                                "套利策略": ["统计套利", "配对交易"],
                                "趋势策略": ["突破", "动量"],
                                "市场中性": ["多空对冲"]
                            },
                            "mastery_level": "目标75%",
                            "applications": ["算法交易", "套利机会捕捉", "市场中性策略"]
                        },
                        {
                            "name": "金融可视化",
                            "technologies": ["Plotly", "Matplotlib", "Seaborn", "ECharts", "D3.js"],
                            "chart_types": {
                                "基础图表": ["K线图", "折线图", "柱状图"],
                                "高级图表": ["热力图", "相关性矩阵", "雷达图"],
                                "交互图表": ["动态仪表板", "实时图表"]
                            },
                            "mastery_level": "目标92%",
                            "applications": ["数据分析报告", "实时监控", "客户展示"]
                        }
                    ],
                    "integration_framework": {
                        "data_layer": ["实时行情", "历史数据", "宏观指标", "新闻舆情"],
                        "compute_layer": ["技术指标", "机器学习", "风险模型", "组合优化"],
                        "application_layer": ["交易策略", "投资建议", "风险预警", "报告生成"],
                        "presentation_layer": ["可视化图表", "实时仪表板", "专业报告", "API"]
                    }
                },
                {
                    "session_id": "report_writing_20260207",
                    "topic": "专业报告写作技能学习",
                    "duration": "8分钟",
                    "areas": [
                        {
                            "name": "数据可视化原理",
                            "concepts": [
                                "视觉感知与认知心理学",
                                "图表类型选择指南",
                                "数据-视觉映射最佳实践",
                                "信息密度与可读性平衡"
                            ],
                            "mastery_level": "目标90%"
                        },
                        {
                            "name": "图表设计美学",
                            "concepts": [
                                "色彩理论与配色方案",
                                "字体选择与排版原则",
                                "布局设计与视觉层次",
                                "品牌一致性设计"
                            ],
                            "mastery_level": "目标85%"
                        },
                        {
                            "name": "叙事逻辑构建",
                            "frameworks": [
                                "金字塔原理（MECE原则）",
                                "故事化数据表达",
                                "逻辑树与问题拆解",
                                "结论先行结构"
                            ],
                            "mastery_level": "目标88%"
                        },
                        {
                            "name": "前端技术栈",
                            "technologies": {
                                "HTML": ["语义化结构", "响应式设计"],
                                "CSS": ["Grid布局", "Flexbox", "动画效果"],
                                "JavaScript": ["交互逻辑", "数据可视化", "DOM操作"]
                            },
                            "mastery_level": "目标82%"
                        },
                        {
                            "name": "Python可视化库",
                            "libraries": {
                                "Matplotlib": ["基础图表", "样式定制", "多图布局"],
                                "Seaborn": ["统计可视化", "高级图表", "美学风格"],
                                "Plotly": ["交互式图表", "仪表板", "在线发布"]
                            },
                            "mastery_level": "目标92%"
                        },
                        {
                            "name": "报告自动化",
                            "technologies": ["Jinja2", "自动化生成", "批量处理"],
                            "mastery_level": "目标78%"
                        }
                    ]
                }
            ],
            "key_insights": [
                "金融分析需要完整的技术栈支撑：数据→计算→应用→展示",
                "风险管理是量化交易的核心，VaR和CVaR是必备工具",
                "机器学习在金融预测中的应用需要谨慎，过度拟合是主要风险",
                "可视化不仅是展示工具，更是洞察数据的手段",
                "自动化报告生成能极大提升工作效率，Jinja2是关键工具"
            ],
            "knowledge_connections": [
                {
                    "source": "实时数据处理",
                    "target": "技术指标计算",
                    "relationship": "提供数据基础",
                    "strength": "强"
                },
                {
                    "source": "技术指标计算",
                    "target": "机器学习预测",
                    "relationship": "特征工程输入",
                    "strength": "强"
                },
                {
                    "source": "机器学习预测",
                    "target": "量化交易策略",
                    "relationship": "信号生成",
                    "strength": "中"
                },
                {
                    "source": "风险管理算法",
                    "target": "投资组合优化",
                    "relationship": "风险约束",
                    "strength": "强"
                },
                {
                    "source": "投资组合优化",
                    "target": "量化交易策略",
                    "relationship": "资产配置指导",
                    "strength": "中"
                },
                {
                    "source": "金融可视化",
                    "target": "报告自动化",
                    "relationship": "视觉呈现",
                    "strength": "强"
                },
                {
                    "source": "数据分析",
                    "target": "叙事逻辑",
                    "relationship": "洞察提炼",
                    "strength": "中"
                }
            ]
        }
        
        # 2. 保存为长期记忆文件
        memory_file = self.consolidation_path / f"daily_memory_{self.today}.json"
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(learning_content, f, ensure_ascii=False, indent=2)
        
        print(f"Daily learning content consolidated: {memory_file}")
        
        return learning_content
    
    def update_knowledge_graph(self, learning_content):
        """更新知识图谱"""
        print("Updating knowledge graph...")
        
        # 构建知识图谱结构
        knowledge_graph = {
            "metadata": {
                "last_updated": self.now.isoformat(),
                "version": "2.0",
                "total_nodes": 0,
                "total_edges": 0
            },
            "nodes": [],
            "edges": []
        }
        
        # 添加金融分析领域节点
        finance_domains = [
            {
                "id": "realtime_data_processing",
                "label": "实时数据处理",
                "type": "core_competency",
                "mastery": 85,
                "technologies": ["Pandas", "NumPy", "Kafka", "WebSocket"],
                "applications": ["实时行情", "交易信号", "风险预警"],
                "related_fields": ["data_engineering", "streaming_computing"]
            },
            {
                "id": "technical_indicators",
                "label": "技术指标计算",
                "type": "core_competency",
                "mastery": 90,
                "indicators": ["SMA", "EMA", "MACD", "RSI", "布林带", "ATR"],
                "applications": ["趋势识别", "信号生成", "市场状态"],
                "related_fields": ["technical_analysis", "quantitative_finance"]
            },
            {
                "id": "ml_prediction",
                "label": "机器学习预测",
                "type": "advanced_capability",
                "mastery": 80,
                "models": ["LSTM", "GRU", "Random Forest", "XGBoost"],
                "applications": ["价格预测", "趋势分类", "异常检测"],
                "related_fields": ["deep_learning", "time_series_analysis"]
            },
            {
                "id": "risk_management",
                "label": "风险管理算法",
                "type": "core_competency",
                "mastery": 88,
                "methods": ["VaR", "CVaR", "压力测试", "蒙特卡洛"],
                "applications": ["风险评估", "资金管理", "极端预警"],
                "related_fields": ["portfolio_theory", "financial_engineering"]
            },
            {
                "id": "portfolio_optimization",
                "label": "投资组合优化",
                "type": "advanced_capability",
                "mastery": 82,
                "models": ["马科维茨", "Black-Litterman", "风险平价"],
                "applications": ["资产配置", "风险分散", "收益优化"],
                "related_fields": ["optimization_theory", "asset_allocation"]
            },
            {
                "id": "quant_trading_strategies",
                "label": "量化交易策略",
                "type": "application_layer",
                "mastery": 75,
                "strategies": ["统计套利", "配对交易", "动量策略"],
                "applications": ["算法交易", "套利捕捉", "市场中性"],
                "related_fields": ["algorithmic_trading", "market_microstructure"]
            },
            {
                "id": "financial_visualization",
                "label": "金融可视化",
                "type": "presentation_layer",
                "mastery": 92,
                "tools": ["Plotly", "Matplotlib", "Seaborn", "ECharts"],
                "applications": ["数据分析", "实时监控", "客户展示"],
                "related_fields": ["data_visualization", "ui_design"]
            }
        ]
        
        # 添加报告写作领域节点
        report_writing_domains = [
            {
                "id": "data_visualization_principles",
                "label": "数据可视化原理",
                "type": "foundation_knowledge",
                "mastery": 90,
                "concepts": ["视觉感知", "图表选择", "信息密度"],
                "applications": ["报告设计", "洞察呈现"],
                "related_fields": ["cognitive_psychology", "information_design"]
            },
            {
                "id": "chart_design_aesthetics",
                "label": "图表设计美学",
                "type": "design_skill",
                "mastery": 85,
                "elements": ["色彩", "字体", "布局", "层次"],
                "applications": ["报告美化", "品牌一致性"],
                "related_fields": ["visual_design", "ux_design"]
            },
            {
                "id": "narrative_logic",
                "label": "叙事逻辑构建",
                "type": "communication_skill",
                "mastery": 88,
                "frameworks": ["金字塔原理", "MECE", "逻辑树"],
                "applications": ["报告结构", "故事化表达"],
                "related_fields": ["critical_thinking", "business_communication"]
            },
            {
                "id": "frontend_tech_stack",
                "label": "前端技术栈",
                "type": "technical_skill",
                "mastery": 82,
                "technologies": ["HTML", "CSS", "JavaScript"],
                "applications": ["报告开发", "交互设计"],
                "related_fields": ["web_development", "interactive_design"]
            },
            {
                "id": "python_viz_libraries",
                "label": "Python可视化库",
                "type": "technical_skill",
                "mastery": 92,
                "libraries": ["Matplotlib", "Seaborn", "Plotly"],
                "applications": ["数据可视化", "图表生成"],
                "related_fields": ["data_science", "scientific_computing"]
            },
            {
                "id": "report_automation",
                "label": "报告自动化",
                "type": "automation_skill",
                "mastery": 78,
                "tools": ["Jinja2", "模板引擎", "CI/CD"],
                "applications": ["批量生成", "版本控制"],
                "related_fields": ["automation", "workflow_optimization"]
            }
        ]
        
        # 合并所有节点
        knowledge_graph["nodes"] = finance_domains + report_writing_domains
        knowledge_graph["metadata"]["total_nodes"] = len(knowledge_graph["nodes"])
        
        # 构建关系边
        edges = [
            {
                "source": "realtime_data_processing",
                "target": "technical_indicators",
                "relationship": "提供数据基础",
                "type": "data_flow",
                "strength": "strong"
            },
            {
                "source": "technical_indicators",
                "target": "ml_prediction",
                "relationship": "特征工程",
                "type": "data_flow",
                "strength": "strong"
            },
            {
                "source": "ml_prediction",
                "target": "quant_trading_strategies",
                "relationship": "信号生成",
                "type": "application",
                "strength": "medium"
            },
            {
                "source": "risk_management",
                "target": "portfolio_optimization",
                "relationship": "风险约束",
                "type": "optimization",
                "strength": "strong"
            },
            {
                "source": "portfolio_optimization",
                "target": "quant_trading_strategies",
                "relationship": "资产配置",
                "type": "guidance",
                "strength": "medium"
            },
            {
                "source": "financial_visualization",
                "target": "report_automation",
                "relationship": "视觉呈现",
                "type": "integration",
                "strength": "strong"
            },
            {
                "source": "data_visualization_principles",
                "target": "financial_visualization",
                "relationship": "理论基础",
                "type": "knowledge",
                "strength": "strong"
            },
            {
                "source": "chart_design_aesthetics",
                "target": "financial_visualization",
                "relationship": "设计指导",
                "type": "enhancement",
                "strength": "medium"
            },
            {
                "source": "narrative_logic",
                "target": "report_automation",
                "relationship": "结构设计",
                "type": "content",
                "strength": "strong"
            },
            {
                "source": "frontend_tech_stack",
                "target": "report_automation",
                "relationship": "技术实现",
                "type": "implementation",
                "strength": "strong"
            },
            {
                "source": "python_viz_libraries",
                "target": "financial_visualization",
                "relationship": "工具支持",
                "type": "implementation",
                "strength": "strong"
            },
            {
                "source": "realtime_data_processing",
                "target": "python_viz_libraries",
                "relationship": "数据供给",
                "type": "integration",
                "strength": "medium"
            }
        ]
        
        knowledge_graph["edges"] = edges
        knowledge_graph["metadata"]["total_edges"] = len(edges)
        
        # 保存知识图谱
        graph_file = self.knowledge_graph_path / "knowledge_graph.json"
        with open(graph_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)
        
        print(f"Knowledge graph updated: {graph_file}")
        print(f"   Nodes: {knowledge_graph['metadata']['total_nodes']}")
        print(f"   Edges: {knowledge_graph['metadata']['total_edges']}")
        
        return knowledge_graph
    
    def create_learning_path(self):
        """创建学习路径"""
        print("Creating learning path...")
        
        learning_path = {
            "current_date": self.today,
            "learning_stages": [
                {
                    "stage": "基础阶段",
                    "duration": "2周",
                    "focus": [
                        "Python数据科学栈巩固",
                        "金融基础知识强化",
                        "统计学与概率论复习"
                    ],
                    "status": "completed"
                },
                {
                    "stage": "进阶阶段",
                    "duration": "3周",
                    "focus": [
                        "技术指标深入理解",
                        "机器学习模型应用",
                        "风险管理算法实现"
                    ],
                    "status": "in_progress"
                },
                {
                    "stage": "高级阶段",
                    "duration": "4周",
                    "focus": [
                        "量化策略开发与回测",
                        "投资组合优化实战",
                        "实时交易系统构建"
                    ],
                    "status": "planned"
                },
                {
                    "stage": "专家阶段",
                    "duration": "持续",
                    "focus": [
                        "前沿技术跟踪（AI、区块链）",
                        "实战案例积累",
                        "知识体系持续优化"
                    ],
                    "status": "planned"
                }
            ],
            "next_steps": [
                "深化LSTM在时间序列预测中的应用",
                "学习多因子模型构建方法",
                "掌握高频数据处理技术",
                "优化报告自动化流程",
                "建立个人量化策略库"
            ]
        }
        
        path_file = self.consolidation_path / "learning_path.json"
        with open(path_file, 'w', encoding='utf-8') as f:
            json.dump(learning_path, f, ensure_ascii=False, indent=2)
        
        print(f"Learning path created: {path_file}")
        
        return learning_path
    
    def generate_consolidation_report(self, learning_content, knowledge_graph, learning_path):
        """生成知识固化报告"""
        print("Generating consolidation report...")
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Consolidation Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #e2e8f0;
        }}
        
        .glass-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            transition: all 0.3s ease;
        }}
        
        .glass-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}
        
        .glow-text {{
            text-shadow: 0 0 20px rgba(139, 92, 246, 0.5);
        }}
        
        .skill-bar {{
            background: linear-gradient(90deg, #8b5cf6 0%, #06b6d4 100%);
            border-radius: 10px;
            height: 8px;
            transition: width 1s ease;
        }}
        
        .node-card {{
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%);
            border: 1px solid rgba(139, 92, 246, 0.3);
        }}
    </style>
</head>
<body class="p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-12">
            <h1 class="text-5xl font-bold mb-4 glow-text bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
                Knowledge Consolidation Report
            </h1>
            <p class="text-xl text-gray-400">Memory Consolidation & Knowledge Graph Update</p>
            <p class="text-sm text-gray-500 mt-2">Generated: {self.now.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <!-- Summary Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
            <div class="glass-card p-6 text-center">
                <div class="text-4xl font-bold text-purple-400 mb-2">{len(learning_content['learning_sessions'])}</div>
                <div class="text-gray-400">Learning Sessions</div>
            </div>
            <div class="glass-card p-6 text-center">
                <div class="text-4xl font-bold text-cyan-400 mb-2">{knowledge_graph['metadata']['total_nodes']}</div>
                <div class="text-gray-400">Knowledge Nodes</div>
            </div>
            <div class="glass-card p-6 text-center">
                <div class="text-4xl font-bold text-green-400 mb-2">{knowledge_graph['metadata']['total_edges']}</div>
                <div class="text-gray-400">Connections</div>
            </div>
            <div class="glass-card p-6 text-center">
                <div class="text-4xl font-bold text-yellow-400 mb-2">{len(learning_content['key_insights'])}</div>
                <div class="text-gray-400">Key Insights</div>
            </div>
        </div>
        
        <!-- Learning Sessions -->
        <div class="glass-card p-8 mb-8">
            <h2 class="text-3xl font-bold mb-6 text-purple-400">Today's Learning Sessions</h2>
            
            {"".join([f"""
            <div class="mb-8 p-6 rounded-lg bg-gradient-to-r from-purple-900/30 to-cyan-900/30 border border-purple-500/30">
                <h3 class="text-2xl font-semibold mb-4 text-cyan-400">{session['topic']}</h3>
                <p class="text-gray-400 mb-4">Duration: {session['duration']}</p>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {"".join([f"""
                    <div class="p-4 rounded-lg bg-black/30">
                        <h4 class="font-semibold text-purple-300 mb-2">{area['name']}</h4>
                        <div class="mb-2">
                            <div class="flex justify-between text-sm text-gray-400 mb-1">
                                <span>Mastery Level</span>
                                <span>{area['mastery_level']}</span>
                            </div>
                            <div class="w-full bg-gray-700 rounded-full h-2">
                                <div class="skill-bar" style="width: {area['mastery_level'].replace('目标', '').replace('%', '')}%"></div>
                            </div>
                        </div>
                    </div>
                    """ for area in session['areas'][:3]])}
                </div>
            </div>
            """ for session in learning_content['learning_sessions']])}
        </div>
        
        <!-- Knowledge Graph Visualization -->
        <div class="glass-card p-8 mb-8">
            <h2 class="text-3xl font-bold mb-6 text-cyan-400">Knowledge Graph Structure</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {"".join([f"""
                <div class="node-card p-4 rounded-lg">
                    <h4 class="font-semibold text-purple-300 mb-2">{node['label']}</h4>
                    <p class="text-sm text-gray-400 mb-2">Type: {node['type']}</p>
                    <p class="text-sm text-gray-400">Mastery: {node['mastery']}%</p>
                </div>
                """ for node in knowledge_graph['nodes'][:9]])}
            </div>
        </div>
        
        <!-- Key Insights -->
        <div class="glass-card p-8 mb-8">
            <h2 class="text-3xl font-bold mb-6 text-green-400">Key Insights</h2>
            
            <div class="grid grid-cols-1 gap-4">
                {"".join([f"""
                <div class="p-4 rounded-lg bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/30">
                    <p class="text-gray-300">{insight}</p>
                </div>
                """ for insight in learning_content['key_insights']])}
            </div>
        </div>
        
        <!-- Learning Path -->
        <div class="glass-card p-8 mb-8">
            <h2 class="text-3xl font-bold mb-6 text-yellow-400">Learning Path</h2>
            
            <div class="space-y-4">
                {"".join([f"""
                <div class="flex items-start p-4 rounded-lg bg-black/30">
                    <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-cyan-500 flex items-center justify-center mr-4">
                        <span class="text-white font-bold">{i+1}</span>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-white mb-2">{stage['stage']}</h4>
                        <p class="text-sm text-gray-400 mb-2">Duration: {stage['duration']}</p>
                        <div class="flex flex-wrap gap-2">
                            {"".join([f'<span class="px-2 py-1 text-xs rounded-full bg-purple-900/50 text-purple-300">{focus}</span>' for focus in stage['focus']])}
                        </div>
                        <p class="text-sm mt-2 {
                            "text-green-400" if stage['status'] == "completed" else 
                            "text-yellow-400" if stage['status'] == "in_progress" else 
                            "text-gray-400"
                        }">Status: {stage['status']}</p>
                    </div>
                </div>
                """ for i, stage in enumerate(learning_path['learning_stages'])])}
            </div>
        </div>
        
        <!-- Knowledge Connections -->
        <div class="glass-card p-8">
            <h2 class="text-3xl font-bold mb-6 text-pink-400">Knowledge Connections</h2>
            
            <div class="space-y-3">
                {"".join([f"""
                <div class="flex items-center p-3 rounded-lg bg-black/30">
                    <span class="text-purple-400 font-semibold w-1/3">{conn['source']}</span>
                    <span class="text-cyan-400 text-center flex-1">-> {conn['relationship']} -></span>
                    <span class="text-green-400 font-semibold w-1/3 text-right">{conn['target']}</span>
                </div>
                """ for conn in learning_content['knowledge_connections']])}
            </div>
        </div>
        
        <!-- Footer -->
        <div class="text-center mt-12 text-gray-500 text-sm">
            <p>JARVIS Memory Consolidation System v2.0</p>
            <p>Memory files: {self.consolidation_path}</p>
            <p>Knowledge graph: {self.knowledge_graph_path}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 保存报告
        report_file = self.consolidation_path / f"consolidation_report_{self.today}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Consolidation report generated: {report_file}")
        
        # 也保存到reports目录
        reports_path = Path("C:/Users/Administrator/Desktop/workspace/PANTHEON_JARVIS/reports")
        public_report = reports_path / f"知识固化报告_{self.today}_{self.now.strftime('%H%M%S')}.html"
        
        with open(public_report, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Public report generated: {public_report}")
        
        return str(public_report)
    
    def run_consolidation(self):
        """执行完整的知识固化流程"""
        print("\n" + "="*60)
        print("Memory Consolidation System Started")
        print("="*60 + "\n")
        
        try:
            # 1. 固化当天学习内容
            learning_content = self.consolidate_daily_learning()
            
            # 2. 更新知识图谱
            knowledge_graph = self.update_knowledge_graph(learning_content)
            
            # 3. 创建学习路径
            learning_path = self.create_learning_path()
            
            # 4. 生成固化报告
            report_path = self.generate_consolidation_report(
                learning_content,
                knowledge_graph,
                learning_path
            )
            
            print("\n" + "="*60)
            print("Memory Consolidation Completed")
            print("="*60 + "\n")
            
            print("Consolidation Statistics:")
            print(f"   - Learning sessions: {len(learning_content['learning_sessions'])}")
            print(f"   - Knowledge nodes: {knowledge_graph['metadata']['total_nodes']}")
            print(f"   - Connections: {knowledge_graph['metadata']['total_edges']}")
            print(f"   - Key insights: {len(learning_content['key_insights'])}")
            print(f"   - Learning stages: {len(learning_path['learning_stages'])}")
            print()
            
            return report_path
            
        except Exception as e:
            print(f"Error during consolidation: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# Main execution
if __name__ == "__main__":
    system = MemoryConsolidationSystem()
    report_path = system.run_consolidation()
    
    if report_path:
        print(f"\nReport path: {report_path}")
        print("\nNext consolidation: Daily at 03:00")
