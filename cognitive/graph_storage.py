"""
Holo-Mem L3: 语义图谱存储模块
基于 NetworkX 实现轻量级知识图谱，用于解决交叉上下文检索问题。
"""

import networkx as nx
import logging
import os
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

log = logging.getLogger("jarvis.memory.graph")

class GraphStorage:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.graph = nx.DiGraph()
        self._load_graph()

    def _load_graph(self):
        """加载图谱"""
        if self.storage_path.exists():
            try:
                self.graph = nx.read_graphml(str(self.storage_path))
                log.info(f"已加载语义图谱: {self.graph.number_of_nodes()} 节点, {self.graph.number_of_edges()} 边")
            except Exception as e:
                log.error(f"加载图谱失败: {e}")
                self.graph = nx.DiGraph()
        else:
            log.info("未找到现有图谱，创建新图谱")
            self.graph = nx.DiGraph()

    def save_graph(self):
        """保存图谱"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            nx.write_graphml(self.graph, str(self.storage_path))
            log.debug("语义图谱已保存")
        except Exception as e:
            log.error(f"保存图谱失败: {e}")

    def add_relation(self, head: str, relation: str, tail: str, **attrs):
        """添加关系 (三元组)，重复添加同一关系时权重 +1"""
        if not head or not tail or not relation:
            return

        now_str = datetime.now().isoformat()

        # 确保节点存在
        if not self.graph.has_node(head):
            self.graph.add_node(head, created_at=now_str)
        if not self.graph.has_node(tail):
            self.graph.add_node(tail, created_at=now_str)
            
        # 检查边是否已存在
        if self.graph.has_edge(head, tail):
            existing = self.graph.get_edge_data(head, tail)
            existing_relation = existing.get('relation', '')
            old_weight = float(existing.get('weight', 1.0))
            
            if existing_relation == relation:
                # 同一关系：权重 +1
                self.graph.edges[head, tail]['weight'] = old_weight + 1.0
                self.graph.edges[head, tail]['last_updated'] = now_str
                log.debug(f"关系权重增强: {head} --[{relation}]--> {tail} (weight={old_weight + 1.0})")
                return
            else:
                # 不同关系：合并为逗号分隔
                merged_relation = f"{existing_relation},{relation}"
                self.graph.edges[head, tail]['relation'] = merged_relation
                self.graph.edges[head, tail]['weight'] = old_weight + 1.0
                self.graph.edges[head, tail]['last_updated'] = now_str
                log.debug(f"关系合并: {head} --[{merged_relation}]--> {tail}")
                return
        
        # 新边
        self.graph.add_edge(head, tail, relation=relation, weight=1.0,
                           created_at=now_str, last_updated=now_str, **attrs)
        log.debug(f"添加关联: {head} --[{relation}]--> {tail}")

    def get_neighbors(self, entity: str, depth: int = 1) -> List[Dict]:
        """
        获取实体的一跳或两跳邻居，按关系权重排序
        Returns:
            List of {"source", "relation", "target", "weight", "direction"}
        """
        if entity not in self.graph:
            return []

        results = []
        
        # 1-hop outgoing
        for neighbor in self.graph.successors(entity):
            edge_data = self.graph.get_edge_data(entity, neighbor)
            results.append({
                "source": entity,
                "relation": edge_data.get("relation", "related_to"),
                "target": neighbor,
                "weight": float(edge_data.get("weight", 1.0)),
                "direction": "out"
            })
            
            # 2-hop (if depth > 1)
            if depth > 1:
                for next_neighbor in self.graph.successors(neighbor):
                    if next_neighbor == entity: continue
                    next_edge = self.graph.get_edge_data(neighbor, next_neighbor)
                    results.append({
                        "source": neighbor,
                        "relation": next_edge.get("relation", "related_to"),
                        "target": next_neighbor, 
                        "weight": float(next_edge.get("weight", 1.0)),
                        "via": neighbor,
                        "direction": "out_2hop"
                    })

        # 1-hop incoming (Who points to me?)
        for predecessor in self.graph.predecessors(entity):
            edge_data = self.graph.get_edge_data(predecessor, entity)
            results.append({
                "source": predecessor,
                "relation": edge_data.get("relation", "related_to"),
                "target": entity,
                "weight": float(edge_data.get("weight", 1.0)),
                "direction": "in"
            })
        
        # 按权重降序排序，优先返回高权重关系
        results.sort(key=lambda x: x.get("weight", 1.0), reverse=True)
        return results

    def simple_search(self, entity_query: str) -> List[str]:
        """
        简单的模糊搜索节点
        """
        matches = []
        entity_lower = entity_query.lower()
        for node in self.graph.nodes():
            if entity_lower in str(node).lower():
                matches.append(node)
        return matches

    def get_central_concepts(self, limit: int = 5) -> List[str]:
        """
        获取图谱中的核心概念（基于度中心性 * 权重）
        用于发现用户最关注的话题或实体
        """
        if self.graph.number_of_nodes() == 0:
            return []
            
        try:
            # 计算加权度中心性
            weighted_scores = {}
            for node in self.graph.nodes():
                total_weight = 0.0
                for _, _, data in self.graph.edges(node, data=True):
                    total_weight += float(data.get('weight', 1.0))
                for _, _, data in self.graph.in_edges(node, data=True):
                    total_weight += float(data.get('weight', 1.0))
                weighted_scores[node] = total_weight
            
            sorted_nodes = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)
            return [node for node, score in sorted_nodes[:limit]]
            
        except Exception as e:
            log.error(f"获取核心概念失败: {e}")
            return []

    def decay_weights(self, decay_factor: float = 0.95, min_weight: float = 0.1):
        """
        全局权重衰减 - 在夜间固化时调用
        让不活跃的关系逐渐降低权重，活跃关系通过 add_relation 保持高权重
        
        Args:
            decay_factor: 衰减系数 (0-1)，每次调用后 weight *= decay_factor
            min_weight: 最小权重，低于此值的边将被移除
        """
        edges_to_remove = []
        
        for u, v, data in self.graph.edges(data=True):
            old_weight = float(data.get('weight', 1.0))
            new_weight = old_weight * decay_factor
            
            if new_weight < min_weight:
                edges_to_remove.append((u, v))
            else:
                self.graph.edges[u, v]['weight'] = new_weight
        
        # 移除过期边
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
        
        # 清理孤立节点
        isolated = list(nx.isolates(self.graph))
        self.graph.remove_nodes_from(isolated)
        
        if edges_to_remove or isolated:
            log.info(f"图谱权重衰减完成: 移除 {len(edges_to_remove)} 条边, {len(isolated)} 个孤立节点")
            self.save_graph()

    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱详细统计"""
        stats = {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "central_concepts": self.get_central_concepts(5),
        }
        if self.graph.number_of_edges() > 0:
            weights = [float(d.get('weight', 1.0)) for _, _, d in self.graph.edges(data=True)]
            stats["avg_weight"] = sum(weights) / len(weights)
            stats["max_weight"] = max(weights)
        return stats

    def get_graph_summary(self) -> str:
        """获取图谱统计摘要"""
        return f"语义图谱包含 {self.graph.number_of_nodes()} 个实体和 {self.graph.number_of_edges()} 条关系。"
