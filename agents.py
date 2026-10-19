"""
Three-Agent Architecture for BTC Trend Detection and Paper Trading.

Agent 1: Trend Watcher - Updates candles & computes Aroon indicators
Agent 2: Signal Filter - Outputs UP/DOWN/SKIP with cooldown logic
Agent 3: Risk/Paper Executor - Simulates paper trades, tracks PnL
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import json

from aroon import AroonCalculator, compute_aroon_signals


class TrendWatcher:
    """
    Agent 1: Trend Watcher

    Fetches BTC OHLC data, updates candle history,
    and computes Aroon indicators.
    """

    def __init__(self, lookback: int = 14, interval: str = '1h'):
        self.lookback = lookback
        self.interval = interval
        self.calculator = AroonCalculator(lookback)
        self.data_df: Optional[pd.DataFrame] = None
        self.validation_report: Optional[dict] = None

    def update_data(self, df: pd.DataFrame) -> Dict:
        """
        Update candle data and compute indicators.

        Args:
            df: DataFrame with BTC OHLC data

        Returns:
            Update report with counts and latest values
        """
        self.data_df = df.copy()

        # Compute Aroon indicators
        self.data_df = self.calculator.calculate(self.data_df)

        latest = self.calculator.get_latest_values(self.data_df)

        report = {
            'data_points': len(df),
            'valid_rows': df.dropna(subset=['aroon_up']).shape[0],
            'latest_aroon_up': latest.get('aroon_up', np.nan),
            'latest_aroon_down': latest.get('aroon_down', np.nan),
            'latest_oscillator': latest.get('aroon_oscillator', np.nan),
            'latest_timestamp': latest.get('timestamp'),
            'lookback_period': self.lookback
        }

        return report

    def get_current_signal(self) -> Tuple[str, float]:
        """
        Get current signal from latest oscillator value.

        Returns:
            Tuple of (signal, oscillator_value)
        """
        if self.data_df is None or len(self.data_df) == 0:
            return ('SKIP', np.nan)

        latest = self.calculator.get_latest_values(self.data_df)
        oscillator = latest.get('aroon_oscillator', np.nan)
        signal = self.calculator.interpret_signal(oscillator)

        return (signal, oscillator)

    def get_dataframe(self) -> pd.DataFrame:
        """Return the current DataFrame with indicators."""
        return self.data_df


class SignalFilter:
    """
    Agent 2: Signal Filter

    Analyzes Aroon indicators and outputs trading signals
    with configurable thresholds and cooldown periods.
    """

    def __init__(self,
                 up_threshold: float = 50,
                 down_threshold: float = -50,
                 cooldown: int = 2):
        self.up_threshold = up_threshold
        self.down_threshold = down_threshold
        self.cooldown = cooldown
        self.signal_history: List[Dict] = []

    def filter_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply signal filtering logic to the data.

        Args:
            df: DataFrame with Aroon indicators

        Returns:
            DataFrame with signals applied
        """
        # Use the pre-computed signals from Aroon module
        df = compute_aroon_signals(
            df,
            lookback=14,  # Assuming standard Aroon calculation
            up_threshold=self.up_threshold,
            down_threshold=self.down_threshold,
            cooldown=self.cooldown
        )

        return df

    def get_last_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get the most recent trading signal."""
        if df is None or 'signal' not in df.columns:
            return None

        latest = df.iloc[-1]
        signal = {
            'timestamp': latest.name if hasattr(latest, 'name') else None,
            'signal': latest['signal'],
            'aroon_up': latest.get('aroon_up', np.nan),
            'aroon_down': latest.get('aroon_down', np.nan),
            'aroon_oscillator': latest.get('aroon_oscillator', np.nan)
        }

        return signal

    def get_signal_counts(self, df: pd.DataFrame) -> Dict[str, int]:
        """Count signals of each type."""
        if df is None or 'signal' not in df.columns:
            return {'UP': 0, 'DOWN': 0, 'SKIP': 0}

        counts = df['signal'].value_counts().to_dict()
        return {
            'UP': counts.get('UP', 0),
            'DOWN': counts.get('DOWN', 0),
            'SKIP': counts.get('SKIP', 0)
        }


class PaperExecutor:
    """
    Agent 3: Risk/Paper Executor

    Simulates paper trades based on signals,
    tracks PnL, manages positions, and never
    interacts with real markets.
    """

    def __init__(self, initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,
                 slippage_bps: float = 5.0):
        """
        Initialize paper trading executor.

        Args:
            initial_capital: Starting paper capital in USD
            fee_rate: Trading fee as decimal (0.1% = 0.001)
            slippage_bps: Slippage in basis points (5 bps = 0.5%)
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps

        # State
        self.cash = initial_capital
        self.position: Optional[Dict] = None  # None = no position
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.pnL_history: List[float] = []

    def _calculate_fill_price(self, price: float, side: str) -> float:
        """Calculate execution price with slippage."""
        # Add slippage
        slippage = price * (self.slippage_bps / 10000)
        if side == 'BUY':
            return price + slippage
        else:
            return price - slippage

    def _calculate_fee(self, amount: float) -> float:
        """Calculate trading fee."""
        return amount * self.fee_rate

    def execute_signal(self, df: pd.DataFrame, signal_idx: Optional[int] = None) -> Dict:
        """
        Execute paper trade based on signal.

        Args:
            df: DataFrame with signals and prices
            signal_idx: Index of signal to process (default: last signal)

        Returns:
            Trade execution result
        """
        if signal_idx is None:
            signal_idx = len(df) - 1

        if signal_idx >= len(df):
            return {'error': 'Signal index out of range'}

        row = df.iloc[signal_idx]
        timestamp = row.name if hasattr(row, 'name') else None
        signal = row.get('signal', 'SKIP')
        price = float(row.get('close', np.nan)) if pd.notna(row.get('close', np.nan)) else np.nan

        if pd.isna(price) or signal == 'SKIP':
            return {'status': 'skip', 'signal': signal, 'timestamp': timestamp}

        result = {
            'timestamp': timestamp,
            'signal': signal,
            'price': price,
            'side': None,
            'shares': None,
            'fee': None,
            'pnl': None
        }

        if signal == 'UP' and self.position is None:
            # OPEN LONG POSITION
            fill_price = self._calculate_fill_price(price, 'BUY')
            value = self.cash * 0.99  # Keep 1% reserve
            shares = value / fill_price
            cost = shares * fill_price
            fee = self._calculate_fee(cost)

            self.position = {
                'entry_price': fill_price,
                'shares': shares,
                'entry_timestamp': timestamp,
                'direction': 'LONG'
            }
            self.cash -= (cost + fee)

            result['side'] = 'BUY'
            result['shares'] = shares
            result['fee'] = fee
            result['fill_price'] = fill_price

        elif signal == 'DOWN' and self.position is not None:
            # CLOSE LONG POSITION
            fill_price = self._calculate_fill_price(price, 'SELL')
            proceeds = self.position['shares'] * fill_price
            fee = self._calculate_fee(proceeds)

            pnl = proceeds - fee - (self.position['shares'] * self.position['entry_price'])
            pnl_pct = pnl / (self.position['shares'] * self.position['entry_price']) * 100

            self.cash += (proceeds - fee)

            trade_record = {
                'timestamp': timestamp,
                'direction': 'CLOSE_LONG',
                'entry_price': self.position['entry_price'],
                'exit_price': fill_price,
                'shares': self.position['shares'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'fee': fee,
                'holding_period': None
            }

            if isinstance(timestamp, pd.Timestamp) and isinstance(self.position['entry_timestamp'], pd.Timestamp):
                trade_record['holding_period'] = (timestamp - self.position['entry_timestamp']).total_seconds() / 3600

            self.trades.append(trade_record)
            self.pnL_history.append(pnl)
            self.position = None

            result['side'] = 'SELL'
            result['pnl'] = pnl
            result['pnl_pct'] = pnl_pct
            result['fee'] = fee

        # Record equity
        current_equity = self.cash
        if self.position is not None:
            current_equity += self.position['shares'] * price

        self.equity_curve.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'position_value': current_equity - self.cash if self.position else 0,
            'total_equity': current_equity,
            'pnl': current_equity - self.initial_capital,
            'pnl_pct': (current_equity - self.initial_capital) / self.initial_capital * 100
        })

        return result

    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio status."""
        total_pnl = sum(self.pnL_history) if self.pnL_history else 0

        summary = {
            'initial_capital': self.initial_capital,
            'current_cash': self.cash,
            'total_pnl': total_pnl,
            'num_trades': len(self.trades),
            'winning_trades': sum(1 for t in self.trades if t['pnl'] > 0),
            'losing_trades': sum(1 for t in self.trades if t['pnl'] < 0),
            'win_rate': len(self.trades) / max(len(self.pnL_history), 1) if self.trades else 0,
            'has_position': self.position is not None,
            'position_direction': self.position['direction'] if self.position else None,
            'position_pnl': None
        }

        if self.position:
            summary['position_entry_price'] = self.position['entry_price']
            summary['position_shares'] = self.position['shares']

        return summary

    def get_equity_curve_df(self) -> pd.DataFrame:
        """Return equity curve as DataFrame."""
        if not self.equity_curve:
            return pd.DataFrame()
        return pd.DataFrame(self.equity_curve)

    def get_trades_df(self) -> pd.DataFrame:
        """Return trade history as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)


class ThreeAgentSystem:
    """
    Main system combining all three agents.

    Workflow:
    1. TrendWatcher fetches data and computes Aroon
    2. SignalFilter analyzes indicators and generates signals
    3. PaperExecutor simulates trades based on signals
    """

    def __init__(self,
                 lookback: int = 14,
                 up_threshold: float = 50,
                 down_threshold: float = -50,
                 cooldown: int = 2,
                 initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,
                 slippage_bps: float = 5.0):
        """
        Initialize the three-agent system.

        Args:
            lookback: Aroon lookback period
            up_threshold: Oscillator threshold for UP signal
            down_threshold: Oscillator threshold for DOWN signal
            cooldown: Minimum periods between signals
            initial_capital: Starting paper capital
            fee_rate: Trading fee rate
            slippage_bps: Slippage in basis points
        """
        self.trend_watcher = TrendWatcher(lookback=lookback)
        self.signal_filter = SignalFilter(
            up_threshold=up_threshold,
            down_threshold=down_threshold,
            cooldown=cooldown
        )
        self.paper_executor = PaperExecutor(
            initial_capital=initial_capital,
            fee_rate=fee_rate,
            slippage_bps=slippage_bps
        )

        self.last_update_report = {}
        self.last_execution_result = {}

    def run(self, df: pd.DataFrame) -> Dict:
        """
        Run the full three-agent pipeline.

        Args:
            df: Raw BTC OHLC DataFrame

        Returns:
            Complete execution report
        """
        # Agent 1: Trend Watcher
        watcher_report = self.trend_watcher.update_data(df)
        self.last_update_report = watcher_report

        # Agent 2: Signal Filter
        df_with_signals = self.signal_filter.filter_signals(df)

        # Agent 3: Paper Executor (execute on last signal)
        execution_result = self.paper_executor.execute_signal(df_with_signals)
        self.last_execution_result = execution_result

        # Compile full report
        report = {
            'timestamp': datetime.now(),
            'watcher_report': watcher_report,
            'latest_signal': self.signal_filter.get_last_signal(df_with_signals),
            'signal_counts': self.signal_filter.get_signal_counts(df_with_signals),
            'execution_result': execution_result,
            'portfolio_summary': self.paper_executor.get_portfolio_summary(),
            'data_length': len(df)
        }

        return report

    def backtest(self, df: pd.DataFrame) -> Dict:
        """
        Run full backtest across all signals.

        Args:
            df: Historical BTC OHLC DataFrame

        Returns:
            Backtest results with performance metrics
        """
        # Reset executor for clean backtest
        self.paper_executor = PaperExecutor(
            initial_capital=self.paper_executor.initial_capital,
            fee_rate=self.paper_executor.fee_rate,
            slippage_bps=self.paper_executor.slippage_bps
        )

        # Update data with indicators
        df_with_signals = self.signal_filter.filter_signals(df)

        # Execute all signals
        for i in range(len(df_with_signals)):
            self.paper_executor.execute_signal(df_with_signals, i)

        # Compute backtest metrics
        summary = self.paper_executor.get_portfolio_summary()
        equity_df = self.paper_executor.get_equity_curve_df()
        trades_df = self.paper_executor.get_trades_df()

        # Calculate additional metrics
        metrics = {
            'total_trades': len(trades_df),
            'win_rate': summary['win_rate'] * 100,
            'total_pnl': summary['total_pnl'],
            'total_pnl_pct': (equity_df['total_equity'].iloc[-1] - self.paper_executor.initial_capital) /
                            self.paper_executor.initial_capital * 100 if len(equity_df) > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(equity_df) if len(equity_df) > 0 else 0,
            'final_equity': equity_df['total_equity'].iloc[-1] if len(equity_df) > 0 else self.paper_executor.initial_capital,
            'avg_holding_period': trades_df['holding_period'].mean() if 'holding_period' in trades_df.columns and not trades_df.empty else None
        }

        return {
            'summary': summary,
            'metrics': metrics,
            'equity_curve': equity_df,
            'trades': trades_df,
            'signals': df_with_signals['signal'].value_counts().to_dict() if 'signal' in df_with_signals.columns else {}
        }

    def _calculate_max_drawdown(self, equity_df: pd.DataFrame) -> float:
        """Calculate maximum drawdown from equity curve."""
        if equity_df.empty or 'total_equity' not in equity_df.columns:
            return 0

        peak = equity_df['total_equity'].cummax()
        drawdown = (peak - equity_df['total_equity']) / peak * 100
        return drawdown.max()
