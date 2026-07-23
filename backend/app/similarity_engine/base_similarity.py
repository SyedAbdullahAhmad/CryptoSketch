from abc import ABC, abstractmethod
import numpy as np


class BaseSimilarityAlgorithm(ABC):
    """
    Any similarity algorithm (DTW, cosine, correlation, euclidean...)
    must implement this interface so the engine can swap algorithms
    without touching the scanner or API layer.
    """

    name: str = "base"

    @abstractmethod
    def score(self, series_a: np.ndarray, series_b: np.ndarray) -> float:
        """
        Return a similarity score in [0, 100], where 100 = identical shape.
        Both series are assumed pre-normalized to the same length/range.
        """
        raise NotImplementedError