# BTC Aroon Trend Agents — Paper Trading Dashboard

Educational dashboard that fetches BTC OHLC data, computes Aroon indicators, issues UP/DOWN/SKIP signals, and simulates paper trades.

## ⚠️ Important Disclaimer

- **PAPER MODE ONLY**: This is an educational simulation. No real money is used.
- **Not Financial Advice**: Aroon indicators are not guaranteed to predict price movements.
- **Unverified Claims**: The viral claim of "Grok Bot" performance (+$268,805 over 177 days) is unverified and should NOT be presented as audited performance.
- **Risk of Loss**: Prediction markets involve risk of loss and may have geographic restrictions.

**Do NOT represent any results as audited or independently proven AI-system performance.**

## Features

- 📊 Fetch BTC OHLC data from Binance/CoinGecko
- 🤖 Three-Agent Architecture:
  - **Trend Watcher**: Computes Aroon Up/Down/Oscillator indicators
  - **Signal Filter**: Generates UP/DOWN/SKIP signals with configurable thresholds and cooldowns
  - **Paper Executor**: Simulates trades with fees and slippage
- 📈 Interactive Streamlit dashboard with charts
- 💰 Paper trading simulation (no real orders)
- 📊 Performance metrics (PnL, win rate, drawdown)

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
# Run the Streamlit app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Configuration

Use the sidebar to configure:

### Data Source
- **Source**: Binance or CoinGecko
- **Interval**: 1h, 4h, or 1d candles
- **Days**: 30-730 days of historical data

### Aroon Parameters
- **Lookback Period (N)**: 7-50 (default: 14)
- **UP Threshold**: Oscillator > threshold = UP signal (default: 50)
- **DOWN Threshold**: Oscillator < threshold = DOWN signal (default: -50)
- **Cooldown**: Minimum periods between signals (default: 2)

### Paper Trading
- **Initial Capital**: Starting paper balance (default: $10,000)
- **Fee Rate**: Trading fee percentage (default: 0.1%)
- **Slippage**: Slippage in basis points (default: 5 bps)

## How It Works

### Aroon Indicator Formula
- **Aroon Up** = 100 × (N - periods_since_highest_high) / N
- **Aroon Down** = 100 × (N - periods_since_lowest_low) / N
- **Oscillator** = Aroon Up - Aroon Down (range: -100 to +100)

### Signal Logic
- **UP**: Oscillator > +50 (bullish trend strength)
- **DOWN**: Oscillator < -50 (bearish trend strength)
- **SKIP**: Oscillator between thresholds (neutral)

### Paper Trading
- Simulates entries/exits based on signals
- Includes fee calculation (0.1% default)
- Includes slippage (5 bps default)
- Tracks equity curve and PnL
- Never contacts real markets or wallets

## Project Structure

```
btc-aroon-paper/
├── app.py                 # Main Streamlit dashboard
├── data_fetcher.py        # BTC data fetching from APIs
├── aroon.py               # Aroon indicator calculations
├── agents.py              # Three-agent architecture
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Safety Notes

1. **No Real Orders**: This system never places real orders or connects to exchanges.
2. **Paper Trading Only**: All trades are simulated with virtual capital.
3. **Educational Purpose**: Designed for learning and demonstration only.
4. **No Financial Advice**: Results are for educational purposes and do not constitute investment advice.

## Testing & Evaluation

To run proper backtesting:
1. Split data into training and out-of-sample periods
2. Report total trades, win rate, net PnL, drawdown, fees
3. Compare against no-skill baseline (buy and hold)
4. Avoid cherry-picking parameters

## Known Limitations

- May suffer from look-ahead bias if not implemented carefully
- Slippage model is simplified
- Does not account for all transaction costs
- No machine learning optimization
- Historical data may have gaps

## Dependencies

See `requirements.txt` for full list.

Core dependencies:
- pandas >= 2.0.0
- numpy >= 1.24.0
- requests >= 2.28.0
- streamlit >= 1.25.0
- plotly >= 5.15.0

## Contributing

This is an educational project. Feel free to fork and modify for learning purposes.

## License

MIT License - See LICENSE file for details.
