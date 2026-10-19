"""
Aroon indicator calculation module.
Computes Aroon Up, Aroon Down, and Aroon Oscillator with configurable lookback.
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate_aroon_up(high: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate Aroon Up indicator.

    Aroon Up = 100 * (lookback - periods_since_highest_high) / lookback

    Args:
        high: Series of high prices
        lookback: Lookback period (N)

    Returns:
        Series of Aroon Up values (0-100)
    """
    # Rolling window to find position of highest high
    def periods_since_high(x):
        if len(x) < lookback:
            return np.nan
        # Position of max value (0-indexed from start of window)
        max_pos = np.argmax(x.values)
        # Periods since highest high = (lookback - 1) - max_pos
        return (lookback - 1) - max_pos

    periods_since_high_series = high.rolling(window=lookback, min_periods=lookback).apply(
        periods_since_high, raw=False
    )

    aroon_up = 100 * (lookback - periods_since_high_series) / lookback
    return aroon_up


def calculate_aroon_down(low: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate Aroon Down indicator.

    Aroon Down = 100 * (lookback - periods_since_lowest_low) / lookback

    Args:
        low: Series of low prices
        lookback: Lookback period (N)

    Returns:
        Series of Aroon Down values (0-100)
    """
    def periods_since_low(x):
        if len(x) < lookback:
            return np.nan
        min_pos = np.argmin(x.values)
        return (lookback - 1) - min_pos

    periods_since_low_series = low.rolling(window=lookback, min_periods=lookback).apply(
        periods_since_low, raw=False
    )

    aroon_down = 100 * (lookback - periods_since_low_series) / lookback
    return aroon_down


def calculate_aroon_oscillator(aroon_up: pd.Series, aroon_down: pd.Series) -> pd.Series:
    """
    Calculate Aroon Oscillator.

    Aroon Oscillator = Aroon Up - Aroon Down
    Range: -100 to +100

    Args:
        aroon_up: Aroon Up series
        aroon_down: Aroon Down series

    Returns:
        Series of Aroon Oscillator values
    """
    return aroon_up - aroon_down


def calculate_aroon_indicators(
    prices: pd.Series,
    lookback: int = 14,
    price_type: str = "high"
) -> pd.Series:
    """
    Calculate a single Aroon indicator.

    Args:
        prices: Series of prices (highs or lows)
        lookback: Lookback period
        price_type: "high" for Aroon Up, "low" for Aroon Down

    Returns:
        Series of indicator values
    """
    if price_type == "high":
        return calculate_aroon_up(prices, lookback)
    elif price_type == "low":
        return calculate_aroon_down(prices, lookback)
    else:
        raise ValueError("price_type must be 'high' or 'low'")


def add_aroon_indicators(df: pd.DataFrame, lookback: int = 14,
                         high_col: str = 'high', low_col: str = 'low') -> pd.DataFrame:
    """
    Add Aroon indicators to DataFrame.

    Args:
        df: DataFrame with OHLC data
        lookback: Lookback period for Aroon calculation
        high_col: Name of high price column
        low_col: Name of low price column

    Returns:
        DataFrame with added Aroon columns
    """
    df = df.copy()

    df['aroon_up'] = calculate_aroon_up(df[high_col], lookback)
    df['aroon_down'] = calculate_aroon_down(df[low_col], lookback)
    df['aroon_oscillator'] = calculate_aroon_oscillator(df['aroon_up'], df['aroon_down'])

    return df


class AroonCalculator:
    """Aroon indicator calculator with configurable parameters."""

    def __init__(self, lookback: int = 14):
        """
        Initialize Aroon calculator.

        Args:
            lookback: Lookback period (default 14, commonly 14 or 25)
        """
        self.lookback = lookback

    def calculate(self, df: pd.DataFrame,
                  high_col: str = 'high',
                  low_col: str = 'low') -> pd.DataFrame:
        """
        Calculate all Aroon indicators for a DataFrame.

        Args:
            df: DataFrame with OHLC data
            high_col: High price column name
            low_col: Low price column name

        Returns:
            DataFrame with Aroon columns added
        """
        return add_aroon_indicators(df, self.lookback, high_col, low_col)

    def get_latest_values(self, df: pd.DataFrame) -> dict:
        """
        Get latest Aroon values.

        Args:
            df: DataFrame with Aroon indicators

        Returns:
            Dictionary with latest values
        """
        if df.empty or 'aroon_up' not in df.columns:
            return {}

        latest = df.iloc[-1]
        return {
            'aroon_up': latest.get('aroon_up', np.nan),
            'aroon_down': latest.get('aroon_down', np.nan),
            'aroon_oscillator': latest.get('aroon_oscillator', np.nan),
            'timestamp': df.index[-1] if len(df) > 0 else None
        }

    def interpret_signal(self, oscillator: float,
                         up_threshold: float = 50,
                         down_threshold: float = -50) -> str:
        """
        Interpret Aroon oscillator value as signal.

        Args:
            oscillator: Current oscillator value
            up_threshold: Threshold for UP signal
            down_threshold: Threshold for DOWN signal

        Returns:
            Signal string: 'UP', 'DOWN', or 'SKIP'
        """
        if pd.isna(oscillator):
            return 'SKIP'
        if oscillator > up_threshold:
            return 'UP'
        elif oscillator < down_threshold:
            return 'DOWN'
        return 'SKIP'


def compute_aroon_signals(df: pd.DataFrame, lookback: int = 14,
                          up_threshold: float = 50, down_threshold: float = -50,
                          cooldown: int = 0) -> pd.DataFrame:
    """
    Compute Aroon signals with cooldown logic.

    Args:
        df: DataFrame with OHLC data
        lookback: Aroon lookback period
        up_threshold: Oscillator threshold for UP signal
        down_threshold: Oscillator threshold for DOWN signal
        cooldown: Minimum periods between signals (0 = no cooldown)

    Returns:
        DataFrame with signals column added
    """
    df = add_aroon_indicators(df, lookback)

    # Generate raw signals
    df['raw_signal'] = df['aroon_oscillator'].apply(
        lambda x: 'UP' if x > up_threshold else ('DOWN' if x < down_threshold else 'SKIP')
    )

    # Apply cooldown
    if cooldown > 0:
        df['signal'] = 'SKIP'
        last_signal_idx = -cooldown - 1

        for i in range(len(df)):
            if df.iloc[i]['raw_signal'] != 'SKIP':
                if i - last_signal_idx > cooldown:
                    df.iloc[i, df.columns.get_loc('signal')] = df.iloc[i]['raw_signal']
                    last_signal_idx = i
                else:
                    df.iloc[i, df.columns.get_loc('signal')] = 'SKIP'
            else:
                df.iloc[i, df.columns.get_loc('signal')] = 'SKIP'
    else:
        df['signal'] = df['raw_signal']

    return df
