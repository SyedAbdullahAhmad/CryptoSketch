from typing import List
import numpy as np


def normalize_series(values: List[float]) -> np.ndarray:
    """
    Min-max normalize a series to the [0, 1] range so price scale
    (e.g. BTC at $60k vs a shitcoin at $0.0001) doesn't affect shape comparison.
    """
    arr = np.array(values, dtype=float)
    v_min, v_max = arr.min(), arr.max()
    if v_max - v_min == 0:
        return np.zeros_like(arr)
    return (arr - v_min) / (v_max - v_min)


def resample_series(values: List[float], target_length: int) -> np.ndarray:
    """
    Resample a series (via linear interpolation) to a fixed number of points,
    so the user's drawing (arbitrary # of points) and market windows
    (fixed # of candles) can be compared on equal footing.
    """
    arr = np.array(values, dtype=float)
    if len(arr) == target_length:
        return arr
    if len(arr) < 2:
        return np.full(target_length, arr[0] if len(arr) else 0.0)

    x_old = np.linspace(0, 1, len(arr))
    x_new = np.linspace(0, 1, target_length)
    return np.interp(x_new, x_old, arr)


def normalize_drawing(points_y: List[float], target_length: int) -> np.ndarray:
    """
    Full pipeline for a hand-drawn chart: resample to target_length points,
    then min-max normalize. Canvas Y is typically inverted (0 = top),
    so callers should flip Y before calling this if needed.
    """
    resampled = resample_series(points_y, target_length)
    return normalize_series(resampled.tolist())


def normalize_window(closes: List[float]) -> np.ndarray:
    """Normalize a market rolling-window's close prices."""
    return normalize_series(closes)