from dataclasses import dataclass, field
from typing import List
import numpy as np


@dataclass
class StructureFeatures:
    slope: float
    trend: str            # "up" | "down" | "sideways" | "reversal_bullish" | "reversal_bearish"
    shape: str             # "up" | "down" | "sideways" | "v" | "inverted_v"
    higher_highs: bool
    higher_lows: bool
    lower_highs: bool
    lower_lows: bool
    volatility_ratio: float
    swing_highs: List[float] = field(default_factory=list)
    swing_lows: List[float] = field(default_factory=list)


def _local_extrema(values: np.ndarray, order: int, mode: str) -> List[int]:
    idx = []
    n = len(values)
    for i in range(order, n - order):
        window = values[i - order: i + order + 1]
        if mode == "high" and values[i] == window.max():
            idx.append(i)
        elif mode == "low" and values[i] == window.min():
            idx.append(i)
    return idx


def extract_features(values: List[float]) -> StructureFeatures:
    """
    Extracts the semantic SHAPE of a series (trend direction, swing
    structure, volatility) so imperfect hand-drawn sketches can be
    compared against market data by intention, not pixel position.
    """
    arr = np.array(values, dtype=float)
    n = len(arr)
    if n < 3:
        return StructureFeatures(
            slope=0.0, trend="sideways", shape="sideways",
            higher_highs=False, higher_lows=False, lower_highs=False, lower_lows=False,
            volatility_ratio=0.0,
        )

    v_min, v_max = float(arr.min()), float(arr.max())
    rng = v_max - v_min
    norm = (arr - v_min) / rng if rng > 0 else np.zeros_like(arr)

    x = np.linspace(0, 1, n)
    slope = float(np.polyfit(x, norm, 1)[0])
    volatility_ratio = float(rng / (np.mean(np.abs(arr)) + 1e-9))

    mid = max(2, n // 2)
    rest = n - mid
    first_half_slope = float(np.polyfit(x[:mid], norm[:mid], 1)[0]) if mid >= 2 else 0.0
    second_half_slope = float(np.polyfit(x[mid:], norm[mid:], 1)[0]) if rest >= 2 else 0.0

    order = max(1, n // 10)
    hi_idx = _local_extrema(arr, order, "high")
    lo_idx = _local_extrema(arr, order, "low")
    swing_highs = [float(arr[i]) for i in hi_idx]
    swing_lows = [float(arr[i]) for i in lo_idx]

    higher_highs = len(swing_highs) >= 2 and all(swing_highs[i] < swing_highs[i + 1] for i in range(len(swing_highs) - 1))
    higher_lows = len(swing_lows) >= 2 and all(swing_lows[i] < swing_lows[i + 1] for i in range(len(swing_lows) - 1))
    lower_highs = len(swing_highs) >= 2 and all(swing_highs[i] > swing_highs[i + 1] for i in range(len(swing_highs) - 1))
    lower_lows = len(swing_lows) >= 2 and all(swing_lows[i] > swing_lows[i + 1] for i in range(len(swing_lows) - 1))

    SLOPE_THRESH = 0.15
    if abs(slope) < SLOPE_THRESH and volatility_ratio < 0.08:
        shape, trend = "sideways", "sideways"
    elif first_half_slope < -SLOPE_THRESH and second_half_slope > SLOPE_THRESH:
        shape, trend = "v", "reversal_bullish"
    elif first_half_slope > SLOPE_THRESH and second_half_slope < -SLOPE_THRESH:
        shape, trend = "inverted_v", "reversal_bearish"
    elif slope > SLOPE_THRESH:
        shape, trend = "up", "up"
    elif slope < -SLOPE_THRESH:
        shape, trend = "down", "down"
    else:
        shape, trend = "sideways", "sideways"

    return StructureFeatures(
        slope=slope, trend=trend, shape=shape,
        higher_highs=higher_highs, higher_lows=higher_lows,
        lower_highs=lower_highs, lower_lows=lower_lows,
        volatility_ratio=volatility_ratio,
        swing_highs=swing_highs, swing_lows=swing_lows,
    )


def generate_reasons(features: StructureFeatures) -> List[str]:
    reasons: List[str] = []
    if features.trend == "up":
        reasons.append("Uptrend")
    elif features.trend == "down":
        reasons.append("Downtrend")
    elif features.trend == "sideways":
        reasons.append("Consolidation / Sideways market")
    elif features.trend == "reversal_bullish":
        reasons.append("Sharp reversal (V shape) — potential bottom")
    elif features.trend == "reversal_bearish":
        reasons.append("Sharp rejection (inverted V) — potential top")

    if features.higher_highs:
        reasons.append("Higher Highs")
    if features.higher_lows:
        reasons.append("Higher Lows")
    if features.lower_highs:
        reasons.append("Lower Highs")
    if features.lower_lows:
        reasons.append("Lower Lows")
    if features.volatility_ratio < 0.08:
        reasons.append("Low volatility")
    return reasons