"""
BTC Trading City Dashboard — Full animated city with moving robots
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

from aroon import calculate_aroon_indicators
from agents import ThreeAgentSystem


st.set_page_config(
    page_title="BTC Trading City",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Full CSS for animated city
st.markdown("""
<style>
/* Base city theme */
.stApp {
    background: linear-gradient(180deg, #0a0a2e 0%, #1a1a4e 30%, #2a2a5e 60%, #1a2a3e 100%);
    color: #e0e0ff;
}

/* Stars background */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(2px 2px at 20px 30px, #eee, transparent),
        radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
        radial-gradient(1px 1px at 90px 40px, #fff, transparent),
        radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.9), transparent);
    background-size: 200px 200px;
    animation: twinkle 4s ease-in-out infinite;
    z-index: -1;
}

@keyframes twinkle {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}

/* Main title with neon glow */
.main-title {
    text-align: center;
    font-size: 3em;
    font-weight: bold;
    background: linear-gradient(90deg, #00ffff, #ff00ff, #00ffff);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shine 3s linear infinite;
    text-shadow: 0 0 30px rgba(0,255,255,0.5);
    margin: 10px 0;
}

@keyframes shine {
    to { background-position: 200% center; }
}

/* Subtitle */
.subtitle {
    text-align: center;
    color: #00ff88;
    font-size: 1.2em;
    letter-spacing: 3px;
    text-transform: uppercase;
}

/* Paper mode banner */
.banner {
    background: linear-gradient(90deg, #ff0044, #ff4488, #ff0044);
    background-size: 200% 100%;
    animation: pulse-bg 2s ease-in-out infinite;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
    font-size: 1.2em;
    margin: 15px 0;
    box-shadow: 0 0 20px rgba(255,0,68,0.5);
}

@keyframes pulse-bg {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Building cards */
.building {
    background: linear-gradient(145deg, #0d1b2a, #1b263b);
    border: 2px solid;
    border-radius: 20px;
    padding: 20px;
    margin: 10px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}

.building.watch { border-color: #00ffff; box-shadow: 0 0 15px rgba(0,255,255,0.3); }
.building.filter { border-color: #ff00ff; box-shadow: 0 0 15px rgba(255,0,255,0.3); }
.building.execute { border-color: #00ff88; box-shadow: 0 0 15px rgba(0,255,136,0.3); }

.building:hover {
    transform: translateY(-5px) scale(1.02);
    box-shadow: 0 10px 30px rgba(0,255,255,0.4);
}

/* Building header */
.building-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 15px;
}

.building-icon {
    font-size: 2.5em;
    animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.building-title {
    font-size: 1.3em;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.watch .building-title { color: #00ffff; }
.filter .building-title { color: #ff00ff; }
.execute .building-title { color: #00ff88; }

/* Robot animation inside building */
.robot-zone {
    height: 80px;
    background: linear-gradient(180deg, rgba(0,0,0,0.3), rgba(0,0,0,0.5));
    border-radius: 10px;
    position: relative;
    overflow: hidden;
    margin: 10px 0;
}

.robot {
    position: absolute;
    font-size: 2em;
    animation: patrol 4s ease-in-out infinite;
    filter: drop-shadow(0 0 10px currentColor);
}

.watch .robot { animation-delay: 0s; }
.filter .robot { animation-delay: 1.3s; }
.execute .robot { animation-delay: 2.6s; }

@keyframes patrol {
    0% { left: 5%; transform: scaleX(1); }
    45% { left: 45%; transform: scaleX(1); }
    50% { left: 45%; transform: scaleX(-1); }
    95% { left: 90%; transform: scaleX(-1); }
    100% { left: 5%; transform: scaleX(1); }
}

/* Floor indicator */
.floor {
    display: flex;
    justify-content: space-around;
    margin-top: 10px;
    padding: 10px;
    background: rgba(0,0,0,0.3);
    border-radius: 8px;
}

.floor-item {
    text-align: center;
    font-size: 0.9em;
}

.floor-value {
    font-size: 1.5em;
    font-weight: bold;
}

.watch .floor-value { color: #00ffff; }
.filter .floor-value { color: #ff00ff; }
.execute .floor-value { color: #00ff88; }

/* Data flow lines */
.flow-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    position: relative;
}

.flow-line {
    height: 4px;
    background: linear-gradient(90deg, #00ffff, #ff00ff, #00ff88);
    border-radius: 2px;
    position: relative;
    overflow: hidden;
    width: 80%;
}

.flow-particle {
    position: absolute;
    width: 20px;
    height: 20px;
    background: radial-gradient(circle, #fff, #00ffff);
    border-radius: 50%;
    animation: flow 2s linear infinite;
    box-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
}

@keyframes flow {
    0% { left: -20px; opacity: 0; }
    10% { opacity: 1; }
    90% { opacity: 1; }
    100% { left: 100%; opacity: 0; }
}

.flow-arrow {
    font-size: 2em;
    color: #fff;
    margin: 0 20px;
    animation: arrow-pulse 1s ease-in-out infinite;
}

@keyframes arrow-pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.2); opacity: 1; }
}

/* Metric cards */
.metric {
    background: linear-gradient(145deg, #0d1b2a, #1b263b);
    border: 1px solid #333;
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}

.metric:hover {
    border-color: #00ffff;
    box-shadow: 0 0 15px rgba(0,255,255,0.3);
    transform: scale(1.05);
}

.metric-value {
    font-size: 2.5em;
    font-weight: bold;
    background: linear-gradient(90deg, #00ffff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-label {
    color: #888;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.8em;
    margin-top: 5px;
}

/* Signal dots */
.signal-dots {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 10px 0;
}

.dot {
    width: 15px;
    height: 15px;
    border-radius: 50%;
    animation: blink 1s ease-in-out infinite;
}

.dot.up { background: #00ff00; box-shadow: 0 0 10px #00ff00; animation-delay: 0s; }
.dot.down { background: #ff0000; box-shadow: 0 0 10px #ff0000; animation-delay: 0.3s; }
.dot.neutral { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; animation-delay: 0.6s; }

@keyframes blink {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

/* Ticker */
.ticker {
    background: rgba(0,0,0,0.5);
    padding: 10px 0;
    overflow: hidden;
    white-space: nowrap;
    border-top: 1px solid #333;
    border-bottom: 1px solid #333;
}

.ticker-content {
    display: inline-block;
    animation: scroll 30s linear infinite;
}

@keyframes scroll {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

.ticker-item {
    display: inline-block;
    padding: 0 30px;
    color: #00ffff;
    font-weight: bold;
}

/* Chart styling */
.chart-container {
    background: linear-gradient(145deg, #0d1b2a, #1b263b);
    border-radius: 15px;
    padding: 15px;
    border: 1px solid #333;
}
</style>
""", unsafe_allow_html=True)


def get_btc_data(days=365):
    """Fetch BTC data."""
    try:
        url = "https://api.binance.com/api/v3/klines"
        start = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        params = {"symbol": "BTCUSDT", "interval": "1h", "startTime": start, "limit": 1000}
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code == 451:
            return get_coingecko(days)

        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume','close_time','quote_asset_volume','number_of_trades','taker_buy_base_volume','taker_buy_quote_volume','ignore'])
        df = df[['timestamp','open','high','low','close','volume']].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for c in ['open','high','low','close','volume']:
            df[c] = df[c].astype(float)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    except:
        return get_coingecko(days)


def get_coingecko(days=365):
    """CoinGecko fallback."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['volume'] = 0
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    except:
        return pd.DataFrame()


def get_live_price():
    """Live BTC price."""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        resp = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=10)
        d = resp.json()
        return {
            'price': float(d['lastPrice']),
            'change': float(d['priceChangePercent']),
            'high': float(d['highPrice']),
            'low': float(d['lowPrice']),
            'vol': float(d['volume'])
        }
    except:
        return None


def main():
    # Session state
    if 'tick' not in st.session_state:
        st.session_state['tick'] = 0
    st.session_state['tick'] += 1

    # Header
    st.markdown('<div class="main-title">🏙️ BTC TRADING CITY</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Autonomous Agent Metropolis • Real-Time Data Pipeline</div>', unsafe_allow_html=True)

    # Banner
    st.markdown('<div class="banner">⚠️ PAPER MODE ONLY — NO REAL MONEY • EDUCATIONAL SIMULATION</div>', unsafe_allow_html=True)

    # Live ticker
    live = get_live_price()
    if live:
        st.markdown(f"""
        <div class="ticker">
            <div class="ticker-content">
                <span class="ticker-item">🚀 BTC: ${live['price']:,.2f}</span>
                <span class="ticker-item">📈 24H: {live['change']:+.2f}%</span>
                <span class="ticker-item">🏔️ High: ${live['high']:,.2f}</span>
                <span class="ticker-item">🏜️ Low: ${live['low']:,.2f}</span>
                <span class="ticker-item">📊 Vol: {live['vol']/1e6:.2f}M BTC</span>
                <span class="ticker-item">🕐 {datetime.now().strftime('%H:%M:%S')}</span>
                <span class="ticker-item">🏙️ City Status: ONLINE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Fetch data
    df = get_btc_data(365)
    if df.empty:
        st.error("Data unavailable")
        return

    # Calculate indicators
    df['aroon_up'] = calculate_aroon_indicators(df['high'], 14, 'high')
    df['aroon_down'] = calculate_aroon_indicators(df['low'], 14, 'low')
    df['aroon_osc'] = df['aroon_up'] - df['aroon_down']
    df['signal'] = df['aroon_osc'].apply(lambda x: 'UP' if x > 50 else ('DOWN' if x < -50 else 'SKIP'))

    # Run agents
    system = ThreeAgentSystem(lookback=14, up_threshold=50, down_threshold=-50, cooldown=2)
    report = system.run(df)
    bt = system.backtest(df)

    # Metrics row
    latest_price = float(df['close'].iloc[-1])
    osc = report['watcher_report'].get('latest_oscillator', 0)

    cols = st.columns(5)
    metrics = [
        (f"${latest_price:,.0f}", "BTC Price"),
        (f"{osc:.1f}", "Aroon Osc"),
        (f"${bt['metrics']['total_pnl']:,.0f}", "Total PnL"),
        (f"{bt['metrics']['win_rate']:.1f}%", "Win Rate"),
        (f"{bt['metrics']['total_trades']}", "Trades")
    ]

    for col, (val, label) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Agent buildings
    st.markdown('<h2 style="text-align:center;color:#00ffff;margin:20px 0;">🏢 AGENT BUILDINGS</h2>', unsafe_allow_html=True)

    bc1, bc2, bc3 = st.columns(3)

    with bc1:
        wr = report['watcher_report']
        st.markdown(f"""
        <div class="building watch">
            <div class="building-header">
                <div class="building-icon">👁️</div>
                <div class="building-title">Trend Watcher</div>
            </div>
            <div class="robot-zone">
                <div class="robot">🤖</div>
            </div>
            <div class="signal-dots">
                <div class="dot up"></div>
                <div class="dot neutral"></div>
                <div class="dot neutral"></div>
            </div>
            <div class="floor">
                <div class="floor-item">
                    <div class="floor-value">{wr.get('latest_aroon_up',0):.0f}</div>
                    <div>Aroon Up</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value">{wr.get('latest_aroon_down',0):.0f}</div>
                    <div>Aroon Down</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value">{wr.get('data_points',0)}</div>
                    <div>Data Points</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with bc2:
        sc = report['signal_counts']
        st.markdown(f"""
        <div class="building filter">
            <div class="building-header">
                <div class="building-icon">🎯</div>
                <div class="building-title">Signal Filter</div>
            </div>
            <div class="robot-zone">
                <div class="robot">🎯</div>
            </div>
            <div class="signal-dots">
                <div class="dot neutral"></div>
                <div class="dot down"></div>
                <div class="dot neutral"></div>
            </div>
            <div class="floor">
                <div class="floor-item">
                    <div class="floor-value" style="color:#00ff00">{sc.get('UP',0)}</div>
                    <div>BUY Signals</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value" style="color:#ff0000">{sc.get('DOWN',0)}</div>
                    <div>SELL Signals</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value">{sc.get('SKIP',0)}</div>
                    <div>Skipped</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with bc3:
        ps = bt['summary']
        st.markdown(f"""
        <div class="building execute">
            <div class="building-header">
                <div class="building-icon">💰</div>
                <div class="building-title">Paper Executor</div>
            </div>
            <div class="robot-zone">
                <div class="robot">💼</div>
            </div>
            <div class="signal-dots">
                <div class="dot neutral"></div>
                <div class="dot neutral"></div>
                <div class="dot up"></div>
            </div>
            <div class="floor">
                <div class="floor-item">
                    <div class="floor-value">{ps['num_trades']}</div>
                    <div>Executed</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value">{ps['win_rate']*100:.0f}%</div>
                    <div>Win Rate</div>
                </div>
                <div class="floor-item">
                    <div class="floor-value">${ps['total_pnl']:.0f}</div>
                    <div>PnL</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Data flow animation
    st.markdown("""
    <div class="flow-container">
        <div class="flow-line">
            <div class="flow-particle" style="animation-delay: 0s"></div>
            <div class="flow-particle" style="animation-delay: 0.5s"></div>
            <div class="flow-particle" style="animation-delay: 1s"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Main chart
    st.markdown('<h2 style="text-align:center;color:#00ffff;margin:20px 0;">📈 MARKET surveillance</h2>', unsafe_allow_html=True)

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.05,
        subplot_titles=('BTC/USDT Price Action', 'Aroon Indicators', 'Oscillator')
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='BTC', increasing_line_color='#00ff88', decreasing_line_color='#ff4444',
        showlegend=False
    ), row=1, col=1)

    # Volume
    colors = ['#00ff88' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#ff4444' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, opacity=0.3, showlegend=False), row=1, col=1)

    # Aroon
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_up'], mode='lines', name='Aroon Up',
                             line=dict(color='#00ffff', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_down'], mode='lines', name='Aroon Down',
                             line=dict(color='#ff00ff', width=2)), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=-50, line_dash="dash", line_color="gray", row=2, col=1)

    # Oscillator
    fig.add_trace(go.Scatter(x=df.index, y=df['aroon_osc'], mode='lines', name='Osc',
                             line=dict(color='#ffff00', width=2)), row=3, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="white", row=3, col=1)

    # Signals
    ups = df[df['signal'] == 'UP']
    downs = df[df['signal'] == 'DOWN']
    if not ups.empty:
        fig.add_trace(go.Scatter(x=ups.index, y=ups['close'], mode='markers',
                                 marker=dict(symbol='triangle-up', size=12, color='#00ff00'),
                                 showlegend=False), row=1, col=1)
    if not downs.empty:
        fig.add_trace(go.Scatter(x=downs.index, y=downs['close'], mode='markers',
                                 marker=dict(symbol='triangle-down', size=12, color='#ff0000'),
                                 showlegend=False), row=1, col=1)

    fig.update_layout(height=550, template='plotly_dark', hovermode='x unified',
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')

    st.plotly_chart(fig, use_container_width=True)

    # Bottom stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric">
            <div class="metric-value">{bt['metrics']['max_drawdown']:.2f}%</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric">
            <div class="metric-value">{bt['metrics']['total_pnl_pct']:.2f}%</div>
            <div class="metric-label">Total Return</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        avg_h = bt['metrics']['avg_holding_period']
        st.markdown(f"""
        <div class="metric">
            <div class="metric-value">{f'{avg_h:.1f}h' if avg_h else '—'}</div>
            <div class="metric-label">Avg Hold</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🏙️ BTC Trading City • Paper Trading Simulation • Not Financial Advice")


if __name__ == "__main__":
    main()
