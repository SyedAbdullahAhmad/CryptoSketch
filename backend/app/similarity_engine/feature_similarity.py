import numpy as np

from app.similarity_engine.base_similarity import BaseSimilarityAlgorithm
from app.features.structure_features import extract_features


class FeatureSimilarity(BaseSimilarityAlgorithm):
    """
    Compares the SHAPE/INTENTION of two series (trend direction, swing
    structure, volatility) rather than exact point-by-point distance.
    Tolerant of different widths, heights, drawing speed, and imperfect
    hand-drawn curves.
    """

    name = "feature"

    def score(self, series_a: np.ndarray, series_b: np.ndarray) -> float:
        fa = extract_features(list(series_a))
        fb = extract_features(list(series_b))

        score = 0.0

        if fa.shape == fb.shape:
            score += 50
        elif fa.trend == fb.trend:
            score += 30

        slope_diff = abs(fa.slope - fb.slope)
        score += max(0.0, 25 - slope_diff * 50)

        if fa.higher_highs == fb.higher_highs:
            score += 5
        if fa.higher_lows == fb.higher_lows:
            score += 5
        if fa.lower_highs == fb.lower_highs:
            score += 5
        if fa.lower_lows == fb.lower_lows:
            score += 5

        vol_diff = abs(fa.volatility_ratio - fb.volatility_ratio)
        score += max(0.0, 5 - vol_diff * 20)

        return round(min(score, 100.0), 2)