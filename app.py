"""
Streamlit Dashboard for BTC Aroon Trend Agents Paper Trading System.

This is the main application that provides a visual interface for:
- Viewing BTC price charts with Aroon indicators
- Monitoring agent status and signals
- Tracking paper trading performance
- Configuring system parameters
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import time

# Add current directory to path
import sys
sys.path.insert(0, '.')

from data_fetcher import fetch_btc_data
from aroon import calculate_aroon_indicators
from agents import ThreeAgentSystem


# Page configuration
st.set_page_config(
    page_title="BTC Aroon Trend Agents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


def get_btc_data_binance(days: int = 365, interval: str = "1h") -> pd.DataFrame:
    """Fetch BTC data from Binance API."""
    try:
        # Calculate timestamp
        start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": interval,
            "startTime": start_time,
            "limit": 1000
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Parse data
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])

        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        return df

    except Exception as e:
        st.error(f"Error fetching Binance data: {e}")
        return pd.DataFrame()


def create_price_chart(df: pd.DataFrame, aroon_up: pd.Series, aroon_down: pd.Series,
                       aroon_osc: pd.Series, signals: pd.Series = None) -> go.Figure:
    """Create candlestick chart with Aroon indicators."""

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.05,
        subplot_titles=('BTC/USDT Price', 'Aroon Up/Down', 'Aroon Oscillator')
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='BTC/USDT',
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )

    # Volume bars
    colors = ['green' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'red'
              for i in range(len(df))]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            marker_color=colors,
            opacity=0.3,
            name='Volume',
            showlegend=False
        ),
        row=1, col=1
    )

    # Aroon Up/Down
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=aroon_up,
            mode='lines',
            name='Aroon Up',
            line=dict(color='green', width=2),
            showlegend=True
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=aroon_down,
            mode='lines',
            name='Aroon Down',
            line=dict(color='red', width=2),
            showlegend=True
        ),
        row=2, col=1
    )

    # Horizontal lines at thresholds
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="UP Threshold", row=2, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
    fig.add_hline(y=-50, line_dash="dash", line_color="gray",
                  annotation_text="DOWN Threshold", row=2, col=1)

    # Aroon Oscillator
    osc_color = ['green' if v > 0 else 'red' for v in aroon_osc]
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=aroon_osc,
            mode='lines',
            name='Aroon Osc',
            line=dict(color='blue', width=2),
            showlegend=True
        ),
        row=3, col=1
    )

    # Signal markers
    if signals is not None and not signals.empty:
        up_signals = df[signals == 'UP']
        down_signals = df[signals == 'DOWN']

        if not up_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=up_signals.index,
                    y=up_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=10, color='green'),
                    name='BUY Signal',
                    showlegend=False
                ),
                row=1, col=1
            )

        if not down_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=down_signals.index,
                    y=down_signals['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=10, color='red'),
                    name='SELL Signal',
                    showlegend=False
                ),
                row=1, col=1
            )

    # Update layout
    fig.update_layout(
        height=800,
        template='plotly_dark',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')

    return fig


def create_equity_curve(equity_df: pd.DataFrame) -> go.Figure:
    """Create equity curve chart."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df['total_equity'],
            mode='lines',
            name='Total Equity',
            line=dict(color='blue', width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df['cash'],
            mode='lines',
            name='Cash',
            line=dict(color='orange', width=2)
        )
    )

    # Add initial capital line
    if len(equity_df) > 0:
        initial_cap = equity_df['total_equity'].iloc[0]
        fig.add_hline(
            y=initial_cap,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Initial: ${initial_cap:,.2f}"
        )

    fig.update_layout(
        template='plotly_dark',
        height=300,
        hovermode='x unified'
    )

    return fig


def create_pnl_chart(pnl_history: list) -> go.Figure:
    """Create PnL chart."""
    if not pnl_history:
        return None

    cumulative_pnl = np.cumsum(pnl_history)

    fig = go.Figure()

    colors = ['green' if p >= 0 else 'red' for p in pnl_history]
    fig.add_trace(
        go.Bar(
            x=list(range(len(pnl_history))),
            y=pnl_history,
            marker_color=colors,
            name='Trade PnL'
        )
    )

    fig.add_trace(
        go.Scatter(
            x=list(range(len(cumulative_pnl))),
            y=cumulative_pnl,
            mode='lines',
            name='Cumulative PnL',
            line=dict(color='yellow', width=2)
        )
    )

    fig.update_layout(
        template='plotly_dark',
        height=300,
        xaxis_title='Trade Number',
        yaxis_title='PnL ($)'
    )

    return fig


def main():
    """Main application entry point."""

    # Sidebar configuration
    st.sidebar.title("⚙️ Configuration")

    # Data source settings
    st.sidebar.header("📊 Data Source")
    data_source = st.sidebar.selectbox(
        "Source",
        ["binance", "coingecko"],
        help="Choose data provider for BTC OHLC data"
    )

    interval = st.sidebar.selectbox(
        "Interval",
        ["1h", "4h", "1d"],
        help="Candle interval for OHLC data"
    )

    days = st.sidebar.slider(
        "Days of Data",
        min_value=30,
        max_value=730,
        value=365,
        step=30,
        help="Number of days of historical data to fetch"
    )

    # Aroon settings
    st.sidebar.header("📈 Aroon Parameters")
    lookback = st.sidebar.slider(
        "Lookback Period (N)",
        min_value=7,
        max_value=50,
        value=14,
        step=1,
        help="Aroon indicator lookback period"
    )

    up_threshold = st.sidebar.slider(
        "UP Threshold",
        min_value=30,
        max_value=80,
        value=50,
        step=5,
        help="Oscillator threshold for UP signal (> this value)"
    )

    down_threshold = st.sidebar.slider(
        "DOWN Threshold",
        min_value=-80,
        max_value=-30,
        value=-50,
        step=5,
        help="Oscillator threshold for DOWN signal (< this value)"
    )

    cooldown = st.sidebar.slider(
        "Cooldown (periods)",
        min_value=0,
        max_value=10,
        value=2,
        help="Minimum periods between signals"
    )

    # Paper trading settings
    st.sidebar.header("💰 Paper Trading")
    initial_capital = st.sidebar.number_input(
        "Initial Capital ($)",
        min_value=1000,
        max_value=1000000,
        value=10000,
        step=1000,
        help="Starting paper trading capital"
    )

    fee_rate = st.sidebar.slider(
        "Fee Rate (%)",
        min_value=0.01,
        max_value=1.0,
        value=0.1,
        step=0.01,
        help="Trading fee percentage"
    ) / 100

    slippage_bps = st.sidebar.slider(
        "Slippage (bps)",
        min_value=0,
        max_value=50,
        value=5,
        step=1,
        help="Slippage in basis points"
    )

    # Main title
    st.title("📈 BTC Aroon Trend Agents — Paper Trading System")
    st.markdown("### Educational Dashboard for BTC Trend Detection and Simulation")

    # PAPER MODE banner
    st.warning("⚠️ **PAPER MODE** — This is a simulation for educational purposes only. No real money is used. Past performance does not guarantee future results.", icon="⚠️")

    # Fetch data
    with st.spinner(f"Fetching {days} days of BTC data from {data_source}..."):
        try:
            if data_source == "binance":
                df = get_btc_data_binance(days, interval)
            else:
                # Use CoinGecko for simplicity
                from data_fetcher import BTCDataFetcher
                fetcher = BTCDataFetcher(source='coingecko', interval=interval)
                df = fetcher.fetch_historical(days)

            if df.empty:
                st.error("No data fetched. Check your internet connection or try a different data source.")
                return

            # Ensure numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return

    # Calculate Aroon indicators
    df['aroon_up'] = calculate_aroon_indicators(df['high'], lookback, price_type='high')
    df['aroon_down'] = calculate_aroon_indicators(df['low'], lookback, price_type='low')
    df['aroon_oscillator'] = df['aroon_up'] - df['aroon_down']

    # Generate signals
    df['signal'] = df['aroon_oscillator'].apply(
        lambda x: 'UP' if x > up_threshold else ('DOWN' if x < down_threshold else 'SKIP')
    )

    # Create the three-agent system
    system = ThreeAgentSystem(
        lookback=lookback,
        up_threshold=up_threshold,
        down_threshold=down_threshold,
        cooldown=cooldown,
        initial_capital=initial_capital,
        fee_rate=fee_rate,
        slippage_bps=slippage_bps
    )

    # Run analysis
    with st.spinner("Running three-agent analysis..."):
        report = system.run(df)
        backtest_results = system.backtest(df)

    # Display key metrics
    st.subheader("📊 Key Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    latest_price = df['close'].iloc[-1]
    price_change = df['close'].iloc[-1] - df['close'].iloc[-2] if len(df) > 1 else 0
    price_change_pct = (price_change / df['close'].iloc[-2] * 100) if len(df) > 1 and df['close'].iloc[-2] != 0 else 0

    with col1:
        st.metric("BTC Price", f"${latest_price:,.2f}", f"${price_change:,.2f} ({price_change_pct:.2f}%)")

    with col2:
        latest_osc = report['watcher_report'].get('latest_oscillator', 0)
        st.metric("Aroon Oscillator", f"{latest_osc:.2f}",
                  "↑ Strong Up" if latest_osc > 50 else "↓ Strong Down" if latest_osc < -50 else "→ Neutral")

    with col3:
        summary = backtest_results['summary']
        st.metric("Total PnL", f"${summary['total_pnl']:,.2f}")

    with col4:
        st.metric("Win Rate", f"{summary['win_rate']*100:.1f}%")

    with col5:
        st.metric("Total Trades", f"{summary['num_trades']}")

    # Agent Status Cards
    st.subheader("🤖 Agent Status")

    agent_col1, agent_col2, agent_col3 = st.columns(3)

    with agent_col1:
        st.info("""
        **Trend Watcher**
        - ✅ Data Updated
        - Lookback: {0}
        - Latest Aroon Up: {1:.1f}
        - Latest Aroon Down: {2:.1f}
        """.format(
            lookback,
            report['watcher_report'].get('latest_aroon_up', 0),
            report['watcher_report'].get('latest_aroon_down', 0)
        ))

    with agent_col2:
        signal_counts = report['signal_counts']
        st.info("""
        **Signal Filter**
        - ✅ Analysis Complete
        - UP Signals: {0}
        - DOWN Signals: {1}
        - SKIP Signals: {2}
        - Cooldown: {3} periods
        """.format(
            signal_counts.get('UP', 0),
            signal_counts.get('DOWN', 0),
            signal_counts.get('SKIP', 0),
            cooldown
        ))

    with agent_col3:
        st.info("""
        **Paper Executor**
        - ✅ Simulation Ready
        - Initial Capital: ${:,.0f}
        - Final Equity: ${:,.2f}
        - Max Drawdown: {:.2f}%
        """.format(
            system.paper_executor.initial_capital,
            backtest_results['metrics']['final_equity'],
            backtest_results['metrics']['max_drawdown']
        ))

    # Charts
    st.subheader("📈 Charts")

    # Main price chart
    st.plotly_chart(
        create_price_chart(df, df['aroon_up'], df['aroon_down'], df['aroon_oscillator'], df['signal']),
        use_container_width=True
    )

    # Bottom row: Equity and PnL
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(create_equity_curve(backtest_results['equity_curve']), use_container_width=True)

    with col2:
        trades_df = backtest_results['trades']
        pnl_list = trades_df['pnl'].tolist() if not trades_df.empty and 'pnl' in trades_df.columns else []
        pnl_chart = create_pnl_chart(pnl_list)
        if pnl_chart:
            st.plotly_chart(pnl_chart, use_container_width=True)

    # Signal table
    st.subheader("📋 Recent Signals")

    recent_signals = df[['close', 'aroon_up', 'aroon_down', 'aroon_oscillator', 'signal']].tail(20).copy()
    recent_signals.index = recent_signals.index.strftime('%Y-%m-%d %H:%M')
    st.dataframe(recent_signals, use_container_width=True)

    # Trade history
    trades_df = backtest_results['trades']
    if not trades_df.empty:
        st.subheader("💼 Trade History")
        st.dataframe(trades_df, use_container_width=True)

    # Performance summary
    st.subheader("📊 Performance Summary")

    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)

    with perf_col1:
        st.metric("Total Return", f"{backtest_results['metrics']['total_pnl_pct']:.2f}%")

    with perf_col2:
        st.metric("Max Drawdown", f"{backtest_results['metrics']['max_drawdown']:.2f}%")

    with perf_col3:
        st.metric("Sharpe Ratio (Approx)", "—")  # Would need risk-free rate

    with perf_col4:
        avg_holding = backtest_results['metrics']['avg_holding_period']
        if avg_holding:
            st.metric("Avg Holding (hrs)", f"{avg_holding:.1f}")
        else:
            st.metric("Avg Holding (hrs)", "—")

    # Disclaimer
    st.markdown("""
    ---
    ### ⚠️ Disclaimer

    This is a **paper trading simulation** for educational purposes only.

    - **No real money is involved**
    - **Past performance does not guarantee future results**
    - **Aroon indicators are not guaranteed to predict price movements**
    - **Prediction markets involve risk of loss**

    Do NOT represent any results as audited or independently proven AI-system performance.
    Never place real orders or claim that signals equal profitable prediction-market positions.
    """, unsafe_allow_html=True)

    # Footer
    st.caption(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data: {data_source} | Interval: {interval}")


if __name__ == "__main__":
    main()
