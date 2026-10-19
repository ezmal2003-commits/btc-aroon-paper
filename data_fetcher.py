"""
Data layer for fetching and validating BTC OHLC data.
Supports multiple data sources and handles missing data, timestamp validation.
"""

import pandas as pd
import numpy as np
import requests
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta


class BTCDataFetcher:
    """Fetch and validate BTC OHLC data from various sources."""

    def __init__(self, source: str = "binance", interval: str = "1h"):
        """
        Initialize data fetcher.

        Args:
            source: Data source ('binance', 'coingecko', 'csv')
            interval: Candle interval ('1m', '5m', '15m', '1h', '4h', '1d')
        """
        self.source = source
        self.interval = interval
        self.base_urls = {
            'binance': 'https://api.binance.com/api/v3/klines',
            'coingecko': 'https://api.coingecko.com/api/v3/coins/bitcoin/ohlc'
        }

    def fetch_from_binance(self, symbol: str = "BTCUSDT", limit: int = 1000,
                           start_time: Optional[int] = None,
                           end_time: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch OHLC data from Binance public API.

        Args:
            symbol: Trading pair symbol
            limit: Number of candles to fetch (max 1000 per request)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            DataFrame with OHLCV data
        """
        params = {
            'symbol': symbol,
            'interval': self.interval,
            'limit': limit
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        response = requests.get(self.base_urls['binance'], params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])

        # Keep only OHLCV columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()

        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        return df

    def fetch_from_coingecko(self, days: int = 90) -> pd.DataFrame:
        """
        Fetch OHLC data from CoinGecko (limited intervals).

        Args:
            days: Number of days of data (1, 7, 14, 30, 90, 180, 365, max)

        Returns:
            DataFrame with OHLC data
        """
        url = f"{self.base_urls['coingecko']}?vs_currency=usd&days={days}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        # CoinGecko doesn't provide volume, add placeholder
        df['volume'] = 0.0

        return df

    def fetch_historical(self, days: int = 365, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """
        Fetch historical data by making multiple requests if needed.

        Args:
            days: Number of days of historical data
            symbol: Trading pair symbol

        Returns:
            Combined DataFrame with OHLCV data
        """
        if self.source == 'binance':
            # Calculate how many requests needed (1000 candles per request)
            interval_minutes = self._interval_to_minutes(self.interval)
            candles_per_day = 24 * 60 // interval_minutes
            total_candles = days * candles_per_day
            num_requests = (total_candles // 1000) + 1

            all_data = []
            end_time = None

            for _ in range(num_requests):
                df = self.fetch_from_binance(symbol=symbol, limit=1000, end_time=end_time)
                if df.empty:
                    break
                all_data.append(df)
                end_time = int(df.index[0].timestamp() * 1000) - 1
                time.sleep(0.1)  # Rate limiting

                if len(df) < 1000:
                    break

            if all_data:
                combined = pd.concat(all_data).drop_duplicates().sort_index()
                # Trim to requested days
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
                combined = combined[combined.index >= cutoff]
                return combined
            return pd.DataFrame()

        elif self.source == 'coingecko':
            return self.fetch_from_coingecko(days=min(days, 365))

        else:
            raise ValueError(f"Unknown source: {self.source}")

    def _interval_to_minutes(self, interval: str) -> int:
        """Convert interval string to minutes."""
        mapping = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        return mapping.get(interval, 60)

    def load_from_csv(self, filepath: str, timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """
        Load OHLC data from CSV file.

        Args:
            filepath: Path to CSV file
            timestamp_col: Name of timestamp column

        Returns:
            DataFrame with OHLCV data
        """
        df = pd.read_csv(filepath)
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df.set_index(timestamp_col, inplace=True)
        df.sort_index(inplace=True)
        return df

    def validate_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Validate OHLC data for common issues.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (cleaned_df, validation_report)
        """
        report = {
            'original_rows': len(df),
            'missing_timestamps': 0,
            'duplicate_timestamps': 0,
            'zero_volume_rows': 0,
            'invalid_ohlc': 0,
            'gaps_filled': 0,
            'cleaned_rows': 0
        }

        if df.empty:
            return df, report

        # Check for duplicate timestamps
        dup_mask = df.index.duplicated(keep='first')
        report['duplicate_timestamps'] = dup_mask.sum()
        if dup_mask.any():
            df = df[~dup_mask]

        # Check for missing timestamps (gaps)
        expected_freq = self._interval_to_minutes(self.interval)
        expected_index = pd.date_range(
            start=df.index.min(),
            end=df.index.max(),
            freq=f'{expected_freq}min'
        )
        missing = expected_index.difference(df.index)
        report['missing_timestamps'] = len(missing)

        # Check for invalid OHLC (high < low, etc.)
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close']) |
            (df['open'] <= 0) |
            (df['high'] <= 0) |
            (df['low'] <= 0) |
            (df['close'] <= 0)
        )
        report['invalid_ohlc'] = invalid_ohlc.sum()
        if invalid_ohlc.any():
            df = df[~invalid_ohlc]

        # Check zero volume
        zero_vol = df['volume'] == 0
        report['zero_volume_rows'] = zero_vol.sum()

        # Forward fill small gaps (up to 3 missing candles)
        if len(missing) > 0 and len(missing) <= 3:
            df = df.reindex(expected_index)
            df = df.ffill()
            report['gaps_filled'] = len(missing)

        report['cleaned_rows'] = len(df)
        return df, report


def fetch_btc_data(source: str = "binance", interval: str = "1h",
                   days: int = 365, csv_path: Optional[str] = None) -> Tuple[pd.DataFrame, dict]:
    """
    Convenience function to fetch and validate BTC data.

    Args:
        source: Data source ('binance', 'coingecko', 'csv')
        interval: Candle interval
        days: Days of historical data
        csv_path: Path to CSV file (if source='csv')

    Returns:
        Tuple of (validated DataFrame, validation report)
    """
    fetcher = BTCDataFetcher(source=source, interval=interval)

    if source == 'csv' and csv_path:
        df = fetcher.load_from_csv(csv_path)
    else:
        df = fetcher.fetch_historical(days=days)

    df, report = fetcher.validate_data(df)
    report['source'] = source
    report['interval'] = interval
    report['days_requested'] = days

    return df, report