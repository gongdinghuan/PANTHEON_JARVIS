#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咨询方法论学习脚本
每30分钟执行一次，持续学习麦肯锡、波士顿咨询等高端方法论
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
import random

# 配置日志
log_dir = "logs/consulting_learning"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"consulting_{datetime.now().strftime('%Y%m%d_%H%M')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ConsultingMethodologyLearning:
    """咨询方法论学习系统"""
    
    def __init__(self):
        self.methodologies = {
            "麦肯锡7S模型": {
                "掌握度": 60,
                "应用场景": ["组织分析", "战略制定", "变革管理"],
                "关键要素": ["战略", "结构", "系统", "共享价值观", "风格", "员工", "技能"]
            },
            "波士顿矩阵": {
                "掌握度": 55,
                "应用场景": ["产品组合分析", "资源分配", "投资决策"],
                "关键要素": ["明星", "现金牛", "问题儿童", "瘦狗"]
            },
            "波特五力模型": {
                "掌握度": 70,
                "应用场景": ["行业分析", "竞争战略", "市场进入"],
                "关键要素": ["供应商议价能力", "购买者议价能力", "潜在进入者", "替代品威胁", "行业竞争"]
            },
            "SWOT分析": {
                "掌握度": 85,
                "应用场景": ["战略规划", "竞争分析", "风险评估"],
                "关键要素": ["优势", "劣势", "机会", "威胁"]
            },
            "PEST分析": {
                "掌握度": 65,
                "应用场景": ["宏观环境分析", "市场研究", "政策影响评估"],
                "关键要素": ["政治", "经济", "社会", "技术"]
            },
            "价值链分析": {
                "掌握度": 50,
                "应用场景": ["竞争优势分析", "成本优化", "价值创造"],
                "关键要素": ["主要活动", "支持活动", "价值环节"]
            },
            "平衡计分卡": {
                "掌握度": 45,
                "应用场景": ["绩效管理", "战略执行", "目标设定"],
                "关键要素": ["财务", "客户", "内部流程", "学习与成长"]
            },
            "情景规划": {
                "掌握度": 40,
                "应用场景": ["战略规划", "风险管理", "未来预测"],
                "关键要素": ["情景构建", "驱动因素", "不确定性分析"]
            },
            "蓝海战略": {
                "掌握度": 35,
                "应用场景": ["创新战略", "市场创造", "价值创新"],
                "关键要素": ["价值曲线", "四步行动框架", "ERRC矩阵"]
            },
            "颠覆性创新理论": {
                "掌握度": 30,
                "应用场景": ["创新管理", "市场颠覆", "技术变革"],
                "关键要素": ["维持性创新", "颠覆性创新", "价值网络"]
            }
        }
        
        self.finance_applications = [
            "投资组合分析",
            "公司估值",
            "风险管理",
            "市场预测",
            "竞争分析",
            "战略规划",
            "绩效评估",
            "并购分析",
            "行业研究",
            "趋势分析"
        ]
        
    def get_current_time(self):
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def learn_methodology(self, methodology_name):
        """学习特定方法论"""
        if methodology_name not in self.methodologies:
            logger.warning(f"未知的方法论: {methodology_name}")
            return False
        
        methodology = self.methodologies[methodology_name]
        old_mastery = methodology["掌握度"]
        
        # 模拟学习过程
        learning_gain = random.randint(1, 5)
        methodology["掌握度"] = min(100, old_mastery + learning_gain)
        
        # 记录学习内容
        application = random.choice(methodology["应用场景"])
        finance_app = random.choice(self.finance_applications)
        
        logger.info(f"学习 {methodology_name}:")
        logger.info(f"  - 掌握度: {old_mastery} → {methodology['掌握度']} (+{learning_gain})")
        logger.info(f"  - 应用场景: {application}")
        logger.info(f"  - 金融应用: {finance_app}")
        logger.info(f"  - 关键要素: {', '.join(methodology['关键要素'][:3])}")
        
        return True
    
    def apply_to_finance_analysis(self, methodology_name):
        """将方法论应用于金融分析"""
        if methodology_name not in self.methodologies:
            return False
        
        methodology = self.methodologies[methodology_name]
        
        # 金融分析应用案例
        finance_cases = {
            "麦肯锡7S模型": [
                "分析金融机构的组织效能",
                "评估投资银行的战略一致性",
                "诊断资产管理公司的变革需求"
            ],
            "波士顿矩阵": [
                "分析基金公司的产品组合",
                "评估股票投资组合的资源配置",
                "制定ETF产品的市场策略"
            ],
            "波特五力模型": [
                "分析银行业的竞争格局",
                "评估保险行业的进入壁垒",
                "研究证券行业的替代品威胁"
            ],
            "SWOT分析": [
                "评估科技股的投资价值",
                "分析新能源行业的竞争态势",
                "制定消费股的投资策略"
            ],
            "PEST分析": [
                "分析宏观政策对股市的影响",
                "评估经济周期对债券市场的影响",
                "研究技术变革对金融科技的影响"
            ]
        }
        
        case = random.choice(finance_cases.get(methodology_name, ["金融分析应用"]))
        
        # 应用效果
        effectiveness = random.randint(60, 95)
        
        logger.info(f"应用 {methodology_name} 于金融分析:")
        logger.info(f"  - 应用案例: {case}")
        logger.info(f"  - 应用效果: {effectiveness}%")
        logger.info(f"  - 掌握度提升: +{random.randint(1, 3)}")
        
        # 提升掌握度
        methodology["掌握度"] = min(100, methodology["掌握度"] + random.randint(1, 3))
        
        return case, effectiveness
    
    def search_latest_consulting_trends(self):
        """搜索最新咨询趋势"""
        search_topics = [
            "麦肯锡最新金融研究报告",
            "波士顿咨询金融科技趋势",
            "贝恩咨询投资策略分析",
            "德勤金融行业洞察",
            "普华永道金融监管趋势",
            "埃森哲数字化转型",
            "罗兰贝格战略咨询",
            "奥纬咨询金融风险",
            "毕马威金融科技",
            "安永区块链金融"
        ]
        
        topic = random.choice(search_topics)
        logger.info(f"搜索最新咨询趋势: {topic}")
        
        # 模拟发现
        discoveries = [
            "发现新的战略分析框架",
            "学习到先进的市场研究方法",
            "掌握最新的数据驱动决策技术",
            "了解数字化转型最佳实践",
            "学习到风险管理创新方法"
        ]
        
        discovery = random.choice(discoveries)
        logger.info(f"趋势发现: {discovery}")
        
        return discovery
    
    def generate_learning_report(self):
        """生成学习报告"""
        total_mastery = sum(m["掌握度"] for m in self.methodologies.values())
        avg_mastery = total_mastery / len(self.methodologies)
        
        # 顶级方法论
        top_methodologies = sorted(
            [(name, data["掌握度"]) for name, data in self.methodologies.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # 需要提升的方法论
        weak_methodologies = sorted(
            [(name, data["掌握度"]) for name, data in self.methodologies.items()],
            key=lambda x: x[1]
        )[:3]
        
        report = {
            "timestamp": self.get_current_time(),
            "total_methodologies": len(self.methodologies),
            "average_mastery": avg_mastery,
            "top_methodologies": top_methodologies,
            "weak_methodologies": weak_methodologies,
            "methodology_details": {
                name: {
                    "mastery": data["掌握度"],
                    "applications": data["应用场景"][:2],
                    "key_elements": data["关键要素"][:3]
                }
                for name, data in self.methodologies.items()
            }
        }
        
        return report
    
    def save_progress(self):
        """保存学习进度"""
        progress_file = "consulting_methodology_progress.json"
        
        progress_data = {
            "last_updated": self.get_current_time(),
            "methodologies": self.methodologies,
            "total_sessions": getattr(self, 'total_sessions', 0) + 1
        }
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.info(f"进度已保存到: {progress_file}")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def run_learning_session(self):
        """运行一次学习会话"""
        logger.info("=" * 60)
        logger.info("开始咨询方法论学习会话")
        logger.info(f"开始时间: {self.get_current_time()}")
        logger.info("=" * 60)
        
        # 记录初始状态
        self.initial_avg = sum(m["掌握度"] for m in self.methodologies.values()) / len(self.methodologies)
        
        # 1. 学习方法论
        logger.info("\n📚 阶段1: 学习方法论")
        methodologies_to_learn = random.sample(list(self.methodologies.keys()), 3)
        for methodology in methodologies_to_learn:
            self.learn_methodology(methodology)
        
        # 2. 金融分析应用
        logger.info("\n💼 阶段2: 金融分析应用")
        for methodology in random.sample(list(self.methodologies.keys()), 2):
            self.apply_to_finance_analysis(methodology)
        
        # 3. 搜索最新趋势
        logger.info("\n🔍 阶段3: 搜索最新咨询趋势")
        self.search_latest_consulting_trends()
        
        # 4. 方法论整合
        logger.info("\n🔄 阶段4: 方法论整合应用")
        integration_examples = [
            "麦肯锡7S + 波士顿矩阵: 组织战略与产品组合的协同分析",
            "波特五力 + SWOT: 行业竞争与内部能力的综合分析",
            "PEST + 情景规划: 宏观环境与未来情景的整合分析",
            "价值链 + 平衡计分卡: 价值创造与绩效管理的系统分析"
        ]
        
        for example in random.sample(integration_examples, 2):
            logger.info(f"方法论整合: {example}")
            # 提升相关方法论掌握度
            for methodology_name in self.methodologies:
                if methodology_name.split()[0] in example:
                    old_mastery = self.methodologies[methodology_name]["掌握度"]
                    self.methodologies[methodology_name]["掌握度"] = min(100, old_mastery + 2)
                    logger.info(f"  - {methodology_name}: {old_mastery} → {self.methodologies[methodology_name]['掌握度']}")
        
        # 生成报告
        logger.info("\n📊 阶段5: 生成学习报告")
        report = self.generate_learning_report()
        
        # 显示结果
        logger.info("\n" + "=" * 60)
        logger.info("学习会话完成")
        logger.info(f"结束时间: {self.get_current_time()}")
        logger.info(f"平均掌握度: {self.initial_avg:.1f} → {report['average_mastery']:.1f}")
        logger.info(f"掌握度提升: {report['average_mastery'] - self.initial_avg:.1f}")
        
        logger.info("\n🏆 顶级方法论:")
        for methodology, mastery in report['top_methodologies']:
            logger.info(f"  - {methodology}: {mastery}")
        
        logger.info("\n📈 需要提升的方法论:")
        for methodology, mastery in report['weak_methodologies']:
            logger.info(f"  - {methodology}: {mastery}")
        
        logger.info("=" * 60)
        
        # 保存进度
        self.save_progress()
        
        return report

def main():
    """主函数"""
    try:
        logger.info("启动咨询方法论学习系统")
        
        # 创建学习实例
        learning = ConsultingMethodologyLearning()
        
        # 运行学习会话
        report = learning.run_learning_session()
        
        # 保存详细报告
        report_file = f"reports/consulting_learning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细报告已保存到: {report_file}")
        
        # 生成HTML报告
        generate_html_report(report, report_file.replace('.json', '.html'))
        
        logger.info("咨询方法论学习完成")
        return True
        
    except Exception as e:
        logger.error(f"学习过程出错: {e}", exc_info=True)
        return False

def generate_html_report(report, html_file):
    """生成HTML格式的报告"""
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>咨询方法论学习报告 - {report['timestamp']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #28a745; padding-bottom: 20px; }}
        .methodology-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .methodology-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; }}
        .methodology-name {{ font-weight: bold; font-size: 18px; margin-bottom: 10px; color: #28a745; }}
        .mastery-bar {{ height: 12px; background: #e9ecef; border-radius: 6px; overflow: hidden; margin: 10px 0; }}
        .mastery-progress {{ height: 100%; background: #28a745; }}
        .summary {{ background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin-right: 30px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #28a745; }}
        .section {{ margin: 30px 0; }}
        .section-title {{ color: #28a745; border-bottom: 1px solid #dee2e6; padding-bottom: 10px; }}
        .application-list {{ list-style-type: none; padding-left: 0; }}
        .application-list li {{ padding: 5px 0; border-bottom: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💼 咨询方法论学习报告</h1>
            <p>生成时间: {report['timestamp']}</p>
        </div>
        
        <div class="summary">
            <h2>📊 学习摘要</h2>
            <div class="metric">
                <div class="metric-label">方法论总数</div>
                <div class="metric-value">{report['total_methodologies']}个</div>
            </div>
            <div class="metric">
                <div class="metric-label">平均掌握度</div>
                <div class="metric-value">{report['average_mastery']:.1f}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">顶级方法论</div>
                <div class="metric-value">{len(report['top_methodologies'])}个</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 方法论掌握度详情</h2>
            <div class="methodology-grid">
    """
    
    # 添加方法论卡片
    for name, details in report['methodology_details'].items():
        html_content += f"""
                <div class="methodology-card">
                    <div class="methodology-name">{name}</div>
                    <div class="mastery-bar">
                        <div class="mastery-progress" style="width: {details['mastery']}%"></div>
                    </div>
                    <div style="margin: 10px 0; font-size: 14px; color: #666;">
                        掌握度: {details['mastery']}/100
                    </div>
                    <div style="margin-top: 15px;">
                        <strong>主要应用:</strong>
                        <ul class="application-list">
        """
        
        for app in details['applications']:
            html_content += f"<li>{app}</li>"
        
        html_content += f"""
                        </ul>
                    </div>
                    <div style="margin-top: 10px; font-size: 12px; color: #888;">
                        <strong>关键要素:</strong> {', '.join(details['key_elements'])}
                    </div>
                </div>
        """
    
    html_content += """
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 顶级方法论</h2>
            <div class="methodology-grid">
    """
    
    # 添加顶级方法论
    for methodology, mastery in report['top_methodologies']:
        details = report['methodology_details'][methodology]
        html_content += f"""
                <div class="methodology-card" style="border-left-color: #007bff; background: #e7f3ff;">
                    <div class="methodology-name" style="color: #007bff;">{methodology}</div>
                    <div class="mastery-bar">
                        <div class="mastery-progress" style="width: {mastery}%; background: #007bff;"></div>
                    </div>
                    <div style="margin: 10px 0; font-size: 14px; color: #666;">
                        掌握度: {mastery}/100
                    </div>
                    <div style="margin-top: 15px;">
                        <strong>金融应用:</strong>
                        <ul class="application-list">
        """
        
        for app in details['applications']:
            html_content += f"<li>{app}</li>"
        
        html_content += """
                        </ul>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📚 下次学习重点</h2>
            <div class="methodology-grid">
    """
    
    # 添加需要提升的方法论
    for methodology, mastery in report['weak_methodologies']:
        details = report['methodology_details'][methodology]
        html_content += f"""
                <div class="methodology-card" style="border-left-color: #dc3545; background: #f8d7da;">
                    <div class="methodology-name" style="color: #dc3545;">{methodology}</div>
                    <div class="mastery-bar">
                        <div class="mastery-progress" style="width: {mastery}%; background: #dc3545;"></div>
                    </div>
                    <div style="margin: 10px 0; font-size: 14px; color: #666;">
                        掌握度: {mastery}/100 (需提升)
                    </div>
                    <div style="margin-top: 15px;">
                        <strong>建议学习:</strong>
                        <ul class="application-list">
        """
        
        for app in details['applications']:
            html_content += f"<li>{app}</li>"
        
        html_content += """
                        </ul>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666;">
            <p>咨询方法论学习系统 | 每30分钟自动学习 | 持续提升战略分析能力</p>
            <p>💡 提示: 掌握度基于模拟学习进度，实际应用需结合具体业务场景</p>
        </div>
    </div>
</body>
</html>
    """
    
    try:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML报告已生成: {html_file}")
    except Exception as e:
        logger.error(f"生成HTML报告失败: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)