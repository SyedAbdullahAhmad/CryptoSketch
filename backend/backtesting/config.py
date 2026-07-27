"""
All tunable parameters live here. Nothing in the engine, trendline
detector, or strategy should hardcode a number that a user might
reasonably want to change -- it should come from one of these configs.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class SwingConfig:
    # A candle is a swing low/high if it is the min/max within
    # `strength` candles on both sides. Higher = fewer, more significant pivots.
    strength: int = 3


@dataclass
class TrendlineConfig:
    # Minimum/maximum slope (price change per candle, normalized by price)
    # to reject "almost flat" or "very steep" trendlines.
    min_slope_pct_per_candle: float = 0.0005
    max_slope_pct_per_candle: float = 0.02

    # How close (as a fraction of price) a candle's low must get to the
    # trendline to count as a "touch".
    touch_tolerance_pct: float = 0.0015

    # A trendline is broken if a candle closes this far below it
    # (fraction of price) -- "no candle has closed meaningfully below it".
    break_tolerance_pct: float = 0.002

    # Minimum quality score (0-100) for a trendline to be tradeable.
    min_quality_score: float = 40.0

    # How many bars of history to search for swing lows when building trendlines.
    lookback_bars: int = 150


@dataclass
class EntryConfig:
    # "Version A": only require the next candle to be green.
    # "Version B": require the green candle to close above the red touch candle's high.
    entry_version: str = "A"  # "A" or "B"


@dataclass
class StopLossConfig:
    method: str = "A"  # "A", "B", or "C"
    atr_period: int = 14
    atr_buffer_multiple: float = 0.25  # used by Method B and C


@dataclass
class TakeProfitConfig:
    method: str = "A"  # "A" (2R), "B" (3R), "C" (swing high), "D" (EMA trail), "E" (trendline trail)
    ema_period: int = 20


@dataclass
class BacktestConfig:
    symbols: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
        "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT",
    ])
    timeframes: List[str] = field(default_factory=lambda: ["30m", "1h"])
    history_days: float = 180.0

    swing: SwingConfig = field(default_factory=SwingConfig)
    trendline: TrendlineConfig = field(default_factory=TrendlineConfig)
    entry: EntryConfig = field(default_factory=EntryConfig)

    # The ACTIVE stop-loss/take-profit config used for a single backtest run
    # (run_backtest.py sets .method on these before each run in the matrix).
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = field(default_factory=TakeProfitConfig)

    # The full lists of methods to iterate over when running the matrix.
    stop_loss_methods: List[str] = field(default_factory=lambda: ["A", "B", "C"])
    take_profit_methods: List[str] = field(default_factory=lambda: ["A", "B", "C", "D", "E"])

    initial_equity: float = 10_000.0
    risk_per_trade_pct: float = 1.0  # % of equity risked per trade, for equity curve simulation

    output_dir: str = "backtest_results"
