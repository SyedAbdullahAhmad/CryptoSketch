import numpy as np
from typing import Dict

from app.similarity_engine.base_similarity import BaseSimilarityAlgorithm
from app.similarity_engine.dtw_similarity import DTWSimilarity


class SimilarityEngine:
    """
    Registry + facade for similarity algorithms. To add a new algorithm
    (cosine, correlation, euclidean...), implement BaseSimilarityAlgorithm
    and register it here — no other module needs to change.
    """

    def __init__(self):
        self._algorithms: Dict[str, BaseSimilarityAlgorithm] = {}
        self.register(DTWSimilarity())

    def register(self, algorithm: BaseSimilarityAlgorithm):
        self._algorithms[algorithm.name] = algorithm

    def get(self, name: str) -> BaseSimilarityAlgorithm:
        if name not in self._algorithms:
            raise ValueError(
                f"Unknown similarity algorithm '{name}'. "
                f"Available: {list(self._algorithms.keys())}"
            )
        return self._algorithms[name]

    def score(self, series_a: np.ndarray, series_b: np.ndarray, algorithm: str = "dtw") -> float:
        return self.get(algorithm).score(series_a, series_b)


similarity_engine = SimilarityEngine()