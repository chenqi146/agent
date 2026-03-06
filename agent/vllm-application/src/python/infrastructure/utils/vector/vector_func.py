from typing import List
import numpy as np

class VectorFunc:
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    @staticmethod
    def normalize_vector(vec: List[float]) -> List[float]:
        """L2 归一化向量"""
        v = np.array(vec)
        norm = np.linalg.norm(v)
        if norm == 0:
            return vec
        return (v / norm).tolist()
