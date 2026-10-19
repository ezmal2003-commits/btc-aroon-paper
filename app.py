"""
BTC Aroon City Dashboard — Animated futuristic trading metropolis
Each agent is a "building" with moving robot characters
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import time
import sys
sys.path.insert(0, '.')

from data_fetcher import fetch_btc_data
from aroon import calculate_aroon_indicators
from agents import ThreeAgentSystem


st.set_page_config(
    page_title="BTC City Dashboard",
    page_icon="🌃",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Custom CSS for futuristic city theme
st.markdown("""
<style>
/* City background */
.stApp {
    background: linear-gradient(180deg, #0a0a1a 0%, #1a1a3a 50%, #0d1b2a 100%);
    color: #e0e0ff;
}

/* Neon glow effects */
.neon-title {
    text-align: center;
    font-size: 2.5em;
    color: #00ffff;
    text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff, 0 0 40px #00ffff;
    margin-bottom: 20px;
}

.neon-subtitle {
    text-align: center;
    color: #ff00ff;
    font-size: 1.2em;
    text-shadow: 0 0 5px #ff00ff;
}

/* Agent buildings */
.agent-card {
    background: linear-gradient(145deg, #1a1a2e, #16213e);
    border: 2px solid #00ffff;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 0 20px rgba(0,255,255,0.3), inset 0 0 20px rgba(0,255,255,0.1);
    transition: all 0.3s ease;
}

.agent-card:hover {
    box-shadow: 0 0 30px rgba(0,255,255,0.6), inset 0 0 30px rgba(0,255,255,0.2);
    transform: translateY(-5px);
}

.agent-card.warning {
    border-color: #ff6b6b;
    box-shadow: 0 0 20px rgba(255,107,107,0.3);
}

/* Bot animation */
.bot-container {
    position: relative;
    height: 100px;
    overflow: hidden;
}

.bot {
    font-size: 40px;
    position: absolute;
    animation: moveBot 3s ease-in-out infinite;
    filter: drop-shadow(0 0 10px currentColor);
}

@keyframes moveBot {
    0%, 100% { left: 10%; transform: scaleX(1); }
    45% { left: 45%; transform: scaleX(1); }
    50% { left: 45%; transform: scaleX(-1); }
    95% { left: 85%; transform: scaleX(-1); }
}

/* Signal lights */
.signal-light {
    display: inline-block;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    margin: 0 5px;
    animation: pulse 1s ease-in-out infinite;
}

.signal-light.up { background: #00ff00; box-shadow: 0 0 10px #00ff00; }
.signal-light.down { background: #ff0000; box-shadow: 0 0 10px #ff0000; }
.signal-light.skip { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
}

/* Moving data flow */
.data-flow {
    height: 3px;
    background: linear-gradient(90deg, transparent, #00ffff, transparent);
    animation: flow 2s linear infinite;
    margin: 10px 0;
}

@keyframes flow {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* Metric cards */
.metric-box {
    background: linear-gradient(145deg, #0f0f23, #1a1a3a);
    border: 1px solid #333;
    border-radius: 10px;
    padding: 15px;
    text-align: center;
}

.metric-value {
    font-size: 2em;
    font-weight: bold;
    color: #00ffff;
    text-shadow: 0 0 10px rgba(0,255,255,0.5);
}

.metric-label {
    font-size: 0.9em;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 2px;
}

/* Plotly dark theme override */
.js-plotly-plot .plotly .modebar {
    top: 10px !important;
    right: 10px !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, #0a0a1a, #1a1a3a) !important;
}

/* Paper mode banner */
.paper-banner {
    background: linear-gradient(90deg, #ff0000, #ff6b6b, #ff0000);
    background-size: 200% 100%;
    animation: bannerGlow 2s ease-in-out infinite;
    padding: 10px 20px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
    margin: 10px 0;
}

@keyframes bannerGlow {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Scrolling ticker */
.ticker-wrap {
    width: 100%;
    overflow: hidden;
    background: #0a0a1a;
    padding: 10px 0;
    border-top: 1px solid #333;
    border-bottom: 1px solid #333;
}

.ticker {
    display: flex;
    animation: ticker 30s linear infinite;
}

@keyframes ticker {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

.ticker-item {
    padding: 0 30px;
    white-space: nowrap;
    color: #00ffff;
}
</style>
""", unsafe_allow_html=True)


def get_btc_data(days=365, interval="1h"):
    """Fetch BTC data with fallback."""
    try:
        url = "https://api.binance.com/api/v3/klines"
        start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        params = {"symbol": "BTCUSDT", "interval": interval, "startTime": start_time, "limit": 1000}
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 451:
            return get_btc_data_coingecko(days)

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
    except Exception:
        return get_btc_data_coingecko(days)


def get_btc_data_coingecko(days=365):
    """Fallback CoinGecko data."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['volume'] = 0
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    except:
        return pd.DataFrame()


def get_live_price():
    """Get live BTC price."""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=10)
        data = response.json()
        return {
            'price': float(data['lastPrice']),
            'change': float(data['priceChangePercent']),
            'high': float(data['highPrice']),
            'low': float(data['lowPrice']),
            'volume': float(data['volume'])
        }
    except:
        return None


def create_city_skyline(fig, height=200):
    """Create animated city skyline background."""
    # Building silhouettes
    buildings = [
        (0.05, 0.3), (0.12, 0.5), (0.2, 0.35), (0.28, 0.6), (0.35, 0.4),
        (0.42, 0.7), (0.5, 0.45), (0.58, 0.65), (0.65, 0.35), (0.72, 0.55),
        (0.8, 0.4), (0.88, 0.6), (0.95, 0.3)
    ]

    for x, h in buildings:
        fig.add_shape(
            type="rect",
            x0=x-0.03, y0=0, x1=x+0.03, y1=h,
            line_color="#1a1a3a",
            fillcolor="#0a0a1a",
            layer="below"
        )

    return fig


def main():
    # Session state for animations
    if 'tick' not in st.session_state:
        st.session_state['tick'] = 0

    st.session_state['tick'] += 1

    # Live price
    live = get_live_price()

    # Main header with city theme
    st.markdown('<div class="neon-title">🌃 BTC CITY — TRADING METROPOLIS</div>', unsafe_allow_html=True)
    st.markdown('<div class="neon-subtitle">Three Agent Buildings • Live Data • Paper Trading</div>', unsafe_allow_html=True)

    # Paper mode banner
    st.markdown('<div class="paper-banner">⚠️ PAPER MODE — NO REAL MONEY • EDUCATIONAL ONLY</div>', unsafe_allow_html=True)

    # Live ticker
    if live:
        st.markdown(f"""
        <div class="ticker-wrap">
            <div class="ticker">
                <span class="ticker-item">🚀 BTC: ${live['price']:,.2f}</span>
                <span class="ticker-item">📈 24H: {live['change']:+.2f}%</span>
                <span class="ticker-item">🏔️ High: ${live['high']:,.2f}</span>
                <span class="ticker-item">🏜️ Low: ${live['low']:,.2f}</span>
                <span class="ticker-item">📊 Volume: {live['volume']/1e6:.2f}M BTC</span>
                <span class="ticker-item">🕐 {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Fetch and process data
    df = get_btc_data(365, "1h")

    if df.empty:
        st.error("Data unavailable")
        return

    # Calculate indicators
    df['aroon_up'] = calculate_aroon_indicators(df['high'], 14, price_type='high')
    df['aroon_down'] = calculate_aroon_indicators(df['low'], 14, price_type='low')
    df['aroon_osc'] = df['aroon_up'] - df['aroon_down']
    df['signal'] = df['aroon_osc'].apply(lambda x: 'UP' if x > 50 else ('DOWN' if x < -50 else 'SKIP'))

    # Run agents
    system = ThreeAgentSystem(lookback=14, up_threshold=50, down_threshold=-50, cooldown=2)
    report = system.run(df)
    backtest = system.backtest(df)

    # Key metrics row
    latest_price = float(df['close'].iloc[-1])
    osc = report['watcher_report'].get('latest_oscillator', 0)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">${latest_price:,.0f}</div>
            <div class="metric-label">BTC Price</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        color = "#00ff00" if osc > 50 else "#ff0000" if osc < -50 else "#ffaa00"
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color: {color}; text-shadow: 0 0 10px {color}">
                {osc:.1f}
            </div>
            <div class="metric-label">Aroon Osc</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">${backtest['metrics']['total_pnl']:,.0f}</div>
            <div class="metric-label">Total PnL</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{backtest['metrics']['win_rate']:.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{backtest['metrics']['total_trades']}</div>
            <div class="metric-label">Trades</div>
        </div>
        """, unsafe_allow_html=True)

    # Data flow animation
    st.markdown('<div class="data-flow"></div>', unsafe_allow_html=True)

    # Three Agent Buildings with animated bots
    st.subheader("🏢 AGENT BUILDINGS")

    ac1, ac2, ac3 = st.columns(3)

    with ac1:
        st.markdown("""
        <div class="agent-card">
            <div style="text-align:center; font-size:24px; color:#00ffff">👁️ TREND WATCHER</div>
            <div class="bot-container">
                <div class="bot" style="animation-delay: 0s">🤖</div>
            </div>
            <div style="text-align:center; margin-top:10px">
                <span class="signal-light up"></span>
                <span class="signal-light skip"></span>
                <span class="signal-light skip"></span>
            </div>
            <hr style="border-color:#333">
            <p style="color:#888; text-align:center">Scanning markets 24/7</p>
            <p style="color:#00ffff; text-align:center; font-size:1.2em">
                Up: {:.1f} | Down: {:.1f}
            </p>
        </div>
        """.format(
            report['watcher_report'].get('latest_aroon_up', 0),
            report['watcher_report'].get('latest_aroon_down', 0)
        ), unsafe_allow_html=True)

    with ac2:
        sc = report['signal_counts']
        st.markdown(f"""
        <div class="agent-card">
            <div style="text-align:center; font-size:24px; color:#ff00ff">🎯 SIGNAL FILTER</div>
            <div class="bot-container">
                <div class="bot" style="animation-delay: 1s; color:#ff00ff">🎯</div>
            </div>
            <div style="text-align:center; margin-top:10px">
                <span class="signal-light up"></span>
                <span class="signal-light down"></span>
                <span class="signal-light skip"></span>
            </div>
            <hr style="border-color:#333">
            <p style="color:#888; text-align:center">Analyzing patterns</p>
            <p style="color:#ff00ff; text-align:center; font-size:1.2em">
                BUY: {sc.get('UP',0)} | SELL: {sc.get('DOWN',0)}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with ac3:
        ps = backtest['summary']
        st.markdown("""
        <div class="agent-card">
            <div style="text-align:center; font-size:24px; color:#00ff00">💼 PAPER EXECUTOR</div>
            <div class="bot-container">
                <div class="bot" style="animation-delay: 2s; color:#00ff00">💰</div>
            </div>
            <div style="text-align:center; margin-top:10px">
                <span class="signal-light skip"></span>
                <span class="signal-light skip"></span>
                <span class="signal-light up"></span>
            </div>
            <hr style="border-color:#333">
            <p style="color:#888; text-align:center">Simulating trades</p>
            <p style="color:#00ff00; text-align:center; font-size:1.2em">
                Trades: {0} | Win: {1:.1f}%
            </p>
        </div>
        """.format(ps['num_trades'], ps['win_rate']*100), unsafe_allow_html=True)

    # Data flow between buildings
    st.markdown("""
    <div style="text-align:center; padding:20px; color:#00ffff; font-size:24px">
        👁️ → 🎯 → 💰
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="data-flow"></div>', unsafe_allow_html=True)

    # Main chart
    st.subheader("📈 MARKET VIEW")

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.05,
        subplot_titles=('BTC/USDT Price Action', 'Aroon Up/Down', 'Aroon Oscillator')
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='BTC', increasing_line_color='green', decreasing_line_color='red',
        showlegend=False
    ), row=1, col=1)

    # Volume
    colors = ['green' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'red' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, opacity=0.3, showlegend=False), row=1, col=1)

    # Aroon lines
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_up'], mode='lines', name='Aroon Up',
                             line=dict(color='green', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_down'], mode='lines', name='Aroon Down',
                             line=dict(color='red', width=2)), row=2, col=1)

    fig.add_hline(y=50, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=-50, line_dash="dash", line_color="gray", row=2, col=1)

    # Oscillator
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_osc'], mode='lines', name='Oscillator',
                             line=dict(color='#00ffff', width=2)), row=3, col=1)

    # Signal markers
    ups = df[df['signal'] == 'UP']
    downs = df[df['signal'] == 'DOWN']

    if not ups.empty:
        fig.add_trace(go.Scatter(x=ups.index, y=ups['close'], mode='markers',
                                 marker=dict(symbol='triangle-up', size=10, color='green'),
                                 showlegend=False), row=1, col=1)
    if not downs.empty:
        fig.add_trace(go.Scatter(x=downs.index, y=downs['close'], mode='markers',
                                 marker=dict(symbol='triangle-down', size=10, color='red'),
                                 showlegend=False), row=1, col=1)

    fig.update_layout(height=600, template='plotly_dark', hovermode='x unified',
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')

    st.plotly_chart(fig, use_container_width=True)

    # Bottom metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Drawdown", f"{backtest['metrics']['max_drawdown']:.2f}%")
    with col2:
        st.metric("Total Return", f"{backtest['metrics']['total_pnl_pct']:.2f}%")
    with col3:
        avg_hold = backtest['metrics']['avg_holding_period']
        st.metric("Avg Hold", f"{avg_hold:.1f}h" if avg_hold else "—")

    # Footer
    st.markdown("---")
    st.caption("🌃 BTC City Dashboard • Paper Trading Simulation • Not Financial Advice")


if __name__ == "__main__":
    main()
