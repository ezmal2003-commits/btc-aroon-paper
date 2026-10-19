"""
Streamlit Dashboard for BTC Aroon Trend Agents Paper Trading System.
Interactive features: real-time updates, comparative backtesting, live price feed.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta, time as dt_time
import time
import sys
sys.path.insert(0, '.')

from data_fetcher import fetch_btc_data
from aroon import calculate_aroon_indicators
from agents import ThreeAgentSystem


st.set_page_config(
    page_title="BTC Aroon Interactive Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state for interactivity
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'btc_price_data' not in st.session_state:
    st.session_state['btc_price_data'] = None
if 'auto_refresh' not in st.session_state:
    st.session_state['auto_refresh'] = False
if 'refresh_count' not in st.session_state:
    st.session_state['refresh_count'] = 0
if 'selected_period' not in st.session_state:
    st.session_state['selected_period'] = '1Y'


def get_btc_data_binance(days: int = 365, interval: str = "1h") -> pd.DataFrame:
    """Fetch BTC data from Binance API with CoinGecko fallback."""
    for attempt in range(3):
        try:
            start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": interval, "startTime": start_time, "limit": 1000}
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 451:
                raise requests.HTTPError("Binance restricted in your region")
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                             'close_time', 'quote_asset_volume', 'number_of_trades',
                                             'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'])
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            return df
        except requests.HTTPError as e:
            if "451" not in str(e) or attempt == 2:
                return get_btc_data_coingecko(days)
        except Exception:
            if attempt == 2:
                return get_btc_data_coingecko(days)
            time.sleep(2)

    return get_btc_data_coingecko(days)


def get_btc_data_coingecko(days: int = 365) -> pd.DataFrame:
    """Fetch BTC data from CoinGecko API as fallback."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['volume'] = 0
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def get_live_btc_price() -> dict:
    """Get live BTC price from Binance."""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=10)
        data = response.json()
        return {
            'price': float(data['lastPrice']),
            'change_24h': float(data['priceChangePercent']),
            'high_24h': float(data['highPrice']),
            'low_24h': float(data['lowPrice']),
            'volume': float(data['volume']),
            'timestamp': datetime.now()
        }
    except:
        return None


def create_interactive_price_chart(df: pd.DataFrame, aroon_up: pd.Series, aroon_down: pd.Series,
                                   aroon_osc: pd.Series, signals: pd.Series = None,
                                   show_signals: bool = True, compare_periods: bool = False) -> go.Figure:
    """Create interactive candlestick chart with multiple time periods."""

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.05,
        subplot_titles=('BTC/USDT Price', 'Aroon Up/Down', 'Aroon Oscillator')
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='BTC/USDT', increasing_line_color='green', decreasing_line_color='red',
        showlegend=False
    ), row=1, col=1)

    # Volume
    colors = ['green' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'red' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, opacity=0.3,
                         name='Volume', showlegend=False), row=1, col=1)

    # Aroon Up/Down
    fig.add_trace(go.Scatter(x=df.index, y=aroon_up, mode='lines', name='Aroon Up',
                             line=dict(color='green', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=aroon_down, mode='lines', name='Aroon Down',
                             line=dict(color='red', width=2)), row=2, col=1)

    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="UP", row=2, col=1)
    fig.add_hline(y=-50, line_dash="dash", line_color="gray", annotation_text="DOWN", row=2, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)

    # Aroon Oscillator
    fig.add_trace(go.Scatter(x=df.index, y=aroon_osc, mode='lines', name='Aroon Osc',
                             line=dict(color='blue', width=2)), row=3, col=1)

    # Signal markers
    if show_signals and signals is not None:
        up_signals = df[signals == 'UP']
        down_signals = df[signals == 'DOWN']

        if not up_signals.empty:
            fig.add_trace(go.Scatter(x=up_signals.index, y=up_signals['close'], mode='markers',
                                     marker=dict(symbol='triangle-up', size=12, color='green',
                                                line=dict(width=2, color='white')),
                                     name='BUY', showlegend=True), row=1, col=1)

        if not down_signals.empty:
            fig.add_trace(go.Scatter(x=down_signals.index, y=down_signals['close'], mode='markers',
                                     marker=dict(symbol='triangle-down', size=12, color='red',
                                                line=dict(width=2, color='white')),
                                     name='SELL', showlegend=True), row=1, col=1)

    fig.update_layout(
        height=700, template='plotly_dark', hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        clickmode='event+select'
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')

    return fig


def create_compare_chart(df_base: pd.DataFrame, df_compare: pd.DataFrame, title: str) -> go.Figure:
    """Compare two periods side by side."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"Current ({len(df_base)} candles)",
                                                        f"Comparison ({len(df_compare)} candles)"))

    for i, (df, row) in enumerate([(df_base, 1), (df_compare, 1)]):
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                     low=df['low'], close=df['close'], showlegend=False), row=row, col=i+1)

    fig.update_layout(height=350, template='plotly_dark', showlegend=False)
    return fig


def main():
    """Main application."""

    # Sidebar
    st.sidebar.title("⚙️ Configuration")

    # Live BTC ticker in sidebar
    live_price = get_live_btc_price()
    if live_price:
        st.sidebar.metric("BTC Live Price", f"${live_price['price']:,.2f}",
                         f"{live_price['change_24h']:+.2f}%")
        st.sidebar.text(f"24h High: ${live_price['high_24h']:,.2f}")
        st.sidebar.text(f"24h Low: ${live_price['low_24h']:,.2f}")
        st.sidebar.text(f"24h Vol: {live_price['volume']/1e6:.2f}M BTC")

    st.sidebar.header("📊 Data Source")
    data_source = st.sidebar.selectbox("Source", ["binance", "coingecko"])
    interval = st.sidebar.selectbox("Interval", ["1h", "4h", "1d"])

    # Quick period buttons
    st.sidebar.header("⏱️ Time Period")
    period_cols = st.sidebar.columns(4)
    period_options = [('1M', 30), ('3M', 90), ('6M', 180), ('1Y', 365)]
    for i, (label, days) in enumerate(period_options):
        if period_cols[i].button(label, key=f'period_{label}'):
            st.session_state['selected_period'] = label

    days_map = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730}
    days = days_map.get(st.session_state['selected_period'], 365)

    st.sidebar.header("📈 Aroon Parameters")
    lookback = st.sidebar.slider("Lookback (N)", 7, 50, 14, 1)
    up_threshold = st.sidebar.slider("UP Threshold", 30, 80, 50, 5)
    down_threshold = st.sidebar.slider("DOWN Threshold", -80, -30, -50, 5)
    cooldown = st.sidebar.slider("Cooldown", 0, 10, 2, 1)

    st.sidebar.header("💰 Paper Trading")
    initial_capital = st.sidebar.number_input("Initial Capital ($)", 1000, 1000000, 10000, 1000)
    fee_rate = st.sidebar.slider("Fee Rate (%)", 0.01, 1.0, 0.1, 0.01) / 100
    slippage_bps = st.sidebar.slider("Slippage (bps)", 0, 50, 5, 1)

    # Auto-refresh toggle
    st.sidebar.header("🔄 Auto Refresh")
    auto_refresh = st.sidebar.toggle("Enable", value=st.session_state['auto_refresh'])
    if auto_refresh != st.session_state['auto_refresh']:
        st.session_state['auto_refresh'] = auto_refresh
        st.session_state['refresh_count'] = 0

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.session_state['last_update'] = None

    # Main title
    st.title("📈 BTC Aroon Trend Agents — Interactive Dashboard")
    st.markdown("### Three-Agent Architecture: Watch • Filter • Execute")
    st.warning("⚠️ **PAPER MODE** — Educational simulation only. No real money.", icon="⚠️")

    # Fetch data
    @st.cache_data(ttl=60)
    def fetch_and_cache(days, interval):
        return get_btc_data_binance(days, interval)

    df = fetch_and_cache(days, interval)

    if df.empty:
        st.error("No data available. Check connection or try different interval.")
        return

    # Calculate indicators
    df['aroon_up'] = calculate_aroon_indicators(df['high'], lookback, price_type='high')
    df['aroon_down'] = calculate_aroon_indicators(df['low'], lookback, price_type='low')
    df['aroon_oscillator'] = df['aroon_up'] - df['aroon_down']
    df['signal'] = df['aroon_oscillator'].apply(
        lambda x: 'UP' if x > up_threshold else ('DOWN' if x < down_threshold else 'SKIP'))

    # Run agents
    system = ThreeAgentSystem(lookback, up_threshold, down_threshold, cooldown,
                              initial_capital, fee_rate, slippage_bps)

    report = system.run(df)
    backtest = system.backtest(df)

    # Key metrics row
    st.subheader("📊 Key Metrics")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        latest_price = float(df['close'].iloc[-1])
        change = float(df['close'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
        st.metric("BTC Price", f"${latest_price:,.0f}", f"${change:,.0f}")
    with c2:
        osc = report['watcher_report'].get('latest_oscillator', 0)
        st.metric("Aroon Osc", f"{osc:.1f}", "↑ Bullish" if osc > 50 else "↓ Bearish" if osc < -50 else "→ Neutral")
    with c3:
        st.metric("Total PnL", f"${backtest['metrics']['total_pnl']:,.0f}")
    with c4:
        st.metric("Win Rate", f"{backtest['metrics']['win_rate']:.1f}%")
    with c5:
        st.metric("Trades", f"{backtest['metrics']['total_trades']}")

    # Chart tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Main Chart", "📊 Performance", "🤖 Agent Status", "📋 Trade Log"])

    with tab1:
        st.subheader("Interactive Price Chart")
        st.plotly_chart(create_interactive_price_chart(df, df['aroon_up'], df['aroon_down'],
                                                        df['aroon_oscillator'], df['signal']),
                       use_container_width=True, key='main_chart')

        # Signal summary
        sig_counts = df['signal'].value_counts()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("BUY Signals", sig_counts.get('UP', 0))
        with col2:
            st.metric("SELL Signals", sig_counts.get('DOWN', 0))
        with col3:
            st.metric("SKIP Signals", sig_counts.get('SKIP', 0))

    with tab2:
        st.subheader("Performance Analytics")

        eq_df = backtest['equity_curve']
        trades_df = backtest['trades']

        col1, col2 = st.columns(2)
        with col1:
            if not eq_df.empty:
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=eq_df.index, y=eq_df['total_equity'],
                                           mode='lines', name='Equity', line=dict(color='blue')))
                fig_eq.add_trace(go.Scatter(x=eq_df.index, y=eq_df['cash'],
                                           mode='lines', name='Cash', line=dict(color='orange')))
                fig_eq.update_layout(height=300, template='plotly_dark', hovermode='x unified')
                st.plotly_chart(fig_eq, use_container_width=True)

        with col2:
            if not trades_df.empty and 'pnl' in trades_df.columns:
                pnl_list = trades_df['pnl'].tolist()
                cum_pnl = np.cumsum(pnl_list)
                fig_pnl = go.Figure()
                fig_pnl.add_trace(go.Bar(x=list(range(len(pnl_list))), y=pnl_list,
                                        marker_color=['green' if p >= 0 else 'red' for p in pnl_list]))
                fig_pnl.add_trace(go.Scatter(x=list(range(len(cum_pnl))), y=cum_pnl,
                                            mode='lines', name='Cumulative', line=dict(color='yellow')))
                fig_pnl.update_layout(height=300, template='plotly_dark',
                                     xaxis_title='Trade #', yaxis_title='PnL ($)')
                st.plotly_chart(fig_pnl, use_container_width=True)

        # Performance metrics grid
        st.subheader("Risk Metrics")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Max Drawdown", f"{backtest['metrics']['max_drawdown']:.2f}%")
        with m2:
            st.metric("Total Return", f"{backtest['metrics']['total_pnl_pct']:.2f}%")
        with m3:
            avg_hold = backtest['metrics']['avg_holding_period']
            st.metric("Avg Hold (hrs)", f"{avg_hold:.1f}" if avg_hold else "—")
        with m4:
            st.metric("Sharpe (Approx)", "—")

    with tab3:
        st.subheader("Agent Status Cards")
        ac1, ac2, ac3 = st.columns(3)

        with ac1:
            wr = report['watcher_report']
            st.info(f"**👁️ Trend Watcher**\n- Data Points: {wr['data_points']}\n- Lookback: {wr['lookback_period']}\n- Aroon Up: {wr.get('latest_aroon_up', 0):.1f}\n- Aroon Down: {wr.get('latest_aroon_down', 0):.1f}")

        with ac2:
            sc = report['signal_counts']
            st.info(f"**🎯 Signal Filter**\n- UP: {sc.get('UP', 0)}\n- DOWN: {sc.get('DOWN', 0)}\n- SKIP: {sc.get('SKIP', 0)}\n- Cooldown: {cooldown} periods")

        with ac3:
            ps = backtest['summary']
            st.info(f"**💼 Paper Executor**\n- Trades: {ps['num_trades']}\n- Win Rate: {ps['win_rate']*100:.1f}%\n- PnL: ${ps['total_pnl']:.2f}\n- Equity: ${backtest['metrics']['final_equity']:.2f}")

    with tab4:
        if not trades_df.empty:
            st.dataframe(trades_df.style.highlight_max(subset=['pnl'], color='green').
                        highlight_min(subset=['pnl'], color='red'), use_container_width=True)
        else:
            st.info("No trades executed yet. Adjust parameters to generate signals.")

    # Live update indicator
    if st.session_state['auto_refresh']:
        st.session_state['refresh_count'] += 1
        st.sidebar.success(f"Auto-refresh #{st.session_state['refresh_count']}")

    # Disclaimer
    st.markdown("---")
    st.caption("📚 Educational simulation only | No real money involved | Not financial advice")


if __name__ == "__main__":
    main()
