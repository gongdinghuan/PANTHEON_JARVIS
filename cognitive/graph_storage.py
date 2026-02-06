"""
Holo-Mem L3: 语义图谱存储模块
基于 NetworkX 实现轻量级知识图谱，用于解决交叉上下文检索问题。
"""

import networkx as nx
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

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
        """添加关系 (三元组)"""
        if not head or not tail or not relation:
            return

        # 确保节点存在
        if not self.graph.has_node(head):
            self.graph.add_node(head)
        if not self.graph.has_node(tail):
            self.graph.add_node(tail)
            
        # 添加或更新边
        # 允许同一对节点间存在多种关系吗？NetworkX DiGraph 不支持多重边。
        # 如果需要支持 "A -> likes -> B" AND "A -> knows -> B"，需要 MultiDiGraph。
        # 这里为了简化，我们使用 DiGraph，如果关系改变则覆盖，或者将关系合并为属性。
        # 简单实现：覆盖旧关系，但记录创建时间
        
        self.graph.add_edge(head, tail, relation=relation, **attrs)
        log.debug(f"添加关联: {head} --[{relation}]--> {tail}")

    def get_neighbors(self, entity: str, depth: int = 1) -> List[Dict]:
        """
        获取实体的一跳或两跳邻居
        Returns:
            List of {"entity": overlap_entity, "relation": rel, "target": neighbor}
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
                "direction": "in"
            })
            
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

    def get_graph_summary(self) -> str:
        """获取图谱统计摘要"""
        return f"语义图谱包含 {self.graph.number_of_nodes()} 个实体和 {self.graph.number_of_edges()} 条关系。"
