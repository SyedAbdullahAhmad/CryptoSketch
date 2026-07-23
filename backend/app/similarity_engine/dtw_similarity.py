import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from app.similarity_engine.base_similarity import BaseSimilarityAlgorithm


class DTWSimilarity(BaseSimilarityAlgorithm):
    """
    Dynamic Time Warping via fastdtw (free, pure-Python/numpy).
    Good default: tolerant of slight stretching/compression in pattern shape,
    which hand-drawn patterns naturally have vs real market data.
    """

    name = "dtw"

    def score(self, series_a: np.ndarray, series_b: np.ndarray) -> float:
        # fastdtw compares one point at a time via `dist`. scipy's euclidean()
        # requires each point to be a 1-D vector, not a bare scalar — so
        # reshape flat series into column vectors: shape (n,) -> (n, 1).
        a = np.asarray(series_a, dtype=float).reshape(-1, 1)
        b = np.asarray(series_b, dtype=float).reshape(-1, 1)

        distance, _ = fastdtw(a, b, dist=euclidean)

        n = max(len(a), len(b))
        max_possible_distance = n * 1.0
        similarity = 1.0 - min(distance / max_possible_distance, 1.0)
        return round(similarity * 100, 2)