# Backend API Documentation

ML backend with 7 algorithms, automated training, RESTful API, and real-time data for 1000+ stocks.

## 🎯 Core Features

- **7 ML Algorithms**: Linear Regression, Random Forest, Decision Tree, KNN, SVM, ARIMA, Autoencoders with automated training
- **Technical Indicators**: 38 features from OHLC data (SMA, EMA, MACD, RSI, Bollinger Bands, ATR)
- **Multi-horizon Forecasting**: 1d/1w/1m/1y/5y predictions via Flask 2.3.3 API with CORS
- **Real-time Data**: Finnhub (US) + Upstox (India) APIs with permanent storage fallback
- **Status Tracking**: `python status.py` (table/JSON/simple formats) with USD/INR currency conversion

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.8 or higher
- **Virtual Environment**: Recommended for dependency isolation
- **Dependencies**: See `requirements.txt`

### Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create empty .env file (required)
# Windows:
type nul > .env
# macOS/Linux:
touch .env

# Start the Flask server
python main.py
```

### Verify Installation
```bash
# Check model status
python status.py

# Test API health
curl "http://localhost:5000/health"

# Test prediction endpoint
curl "http://localhost:5000/api/predict?symbol=AAPL&horizon=1d"
```

## 🔌 API Endpoints

### Prediction Endpoints

| Endpoint | Method | Description | Query Parameters |
|----------|--------|-------------|------------------|
| `/api/predict` | GET | Get ML price prediction | `symbol`, `horizon` (1d/1w/1m/1y/5y), `model` (optional) |
| `/api/train` | POST | Train models for a symbol | Body: `{"symbol": "AAPL", "models": ["random_forest"]}` |
| `/api/models/<symbol>` | GET | List trained models | Path: `symbol` |

### Data Endpoints

| Endpoint | Method | Description | Query Parameters |
|----------|--------|-------------|------------------|
| `/live_price` | GET | Get current stock price | `symbol`, `category` (optional) |
| `/latest_prices` | GET | Get latest prices for all stocks | `category` (us_stocks/ind_stocks, optional) |
| `/historical` | GET | Get historical OHLC data | `symbol`, `period` (5d/1mo/3mo/6mo/1y/2y/5y/max) |
| `/search` | GET | Fuzzy search for stocks | `q` (query string), `limit` (optional, default 10) |
| `/symbols` | GET | Get all available symbols | `category` (optional) |

### Utility Endpoints

| Endpoint | Method | Description | Query Parameters |
|----------|--------|-------------|------------------|
| `/health` | GET | API health check | None |
| `/stock_info` | GET | Get stock metadata | `symbol` |
| `/convert_currency` | GET | Convert USD to INR or vice versa | `amount`, `from_currency`, `to_currency` |

## 📖 Usage Examples

```bash
# Predictions
curl "http://localhost:5000/api/predict?symbol=AAPL&horizon=1d"
curl "http://localhost:5000/api/predict?symbol=AAPL&horizon=1w&model=random_forest"

# Data fetching
curl "http://localhost:5000/live_price?symbol=AAPL"
curl "http://localhost:5000/historical?symbol=AAPL&period=1y"
curl "http://localhost:5000/search?q=apple&limit=5"

# Currency conversion
curl "http://localhost:5000/convert_currency?amount=100&from_currency=USD&to_currency=INR"

# Response: {"success": true, "data": {...}, "error": null}
```

## 🧠 Model Training System

### Current Status (4/7 Trained)
- ✅ **Linear Regression** (R²=-0.002)
- ✅ **Decision Tree** (R²=0.001)
- ✅ **Random Forest** (R²=0.024) - Best performer
- ✅ **SVM** (R²=-0.0055)
- 🔄 **KNN** - Next to train
- ⏳ **ARIMA** - Pending
- ⏳ **Autoencoder** - Pending

### Training Commands
```bash
# Train individual models
python training/basic_models/linear_regression/trainer.py
python training/basic_models/random_forest/trainer.py
python training/advanced_models/knn/trainer.py

# Train all models
python training/train_full_dataset.py

# Check training status
python status.py
```

**Detailed Guide**: See [Training Documentation](../documentation/TRAINING.md)

## 🧮 Feature Engineering

38 technical indicators: Price (2), Moving Averages (10), Volatility (1), Momentum (1), Intraday (2), Position (1), Lagged (5), Rolling Stats (9), Time (3), Raw OHLC (3).  
**Note**: Volume data NOT used in ML calculations.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5000
HOST=0.0.0.0

# Data Configuration
DATA_DIR=../data
PERMANENT_DIR=../permanent
MODEL_SAVE_DIR=backend/models
LOG_DIR=backend/logs

# API Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# API Keys (Optional - for live data)
FINNHUB_API_KEY=your_finnhub_api_key_here
UPSTOX_CLIENT_ID=your_upstox_client_id_here
UPSTOX_CLIENT_SECRET=your_upstox_secret_here
UPSTOX_REDIRECT_URI=http://localhost:3000

# Optional: Cache settings
CACHE_DIR=backend/_cache
CACHE_EXPIRY_HOURS=24
```

### API Keys Setup (Optional)

**Finnhub** (https://finnhub.io): Free tier available  
**Upstox** (https://upstox.com/developer): Requires OAuth setup  
**Guide**: [Upstox Integration](../documentation/UPSTOX_INTEGRATION.md)

## 📋 Data Requirements

### ISIN Codes

**Indian Stocks**: Require ISINs (INExxxxxxxx) - 100% verified for Upstox API  
**US Stocks**: Use ticker symbols only (no ISINs needed for Finnhub API)

### Data Sources

**Real-time**: Finnhub (US) + Upstox (India) → Permanent storage fallback  
**Historical**: yfinance (2020-2025, 5yr) for both markets  
**Permanent Storage**: `permanent/` directory with 1,001 stocks (501 US + 500 Indian), 936 used for training after filtering

## 🧪 Testing

```bash
pytest                                  # All tests
pytest tests/unit/                      # Unit tests (algorithms, data, currency, indicators)
pytest tests/integration/               # Integration tests (API, training, data flow)
pytest --cov=algorithms --cov=main      # With coverage
python tests/manual/test_finnhub.py     # Manual interactive tests
```

## 📝 Logging

Logs in `backend/logs/`: `app.log`, `training.log`, `prediction.log`, `error.log`, `api.log`. Enable debug: Set `FLASK_DEBUG=True` and `LOG_LEVEL=DEBUG` in `.env`.

## ⚡ Performance

API: <100ms | Prediction: <1s (RF/DT) | Training: 5-180min (LR:5-10min, RF:10-15min, DT:5-10min, KNN:15-25min, SVM:20-30min, ANN:30-45min, CNN:45-75min, Autoencoder:40-60min, ARIMA:90-180min) | Memory: 2-8GB peak | Data load: 10-30s (1000+ stocks) | Model size: 1-50MB

**Tips**: Enable caching, permanent storage fallback, limit stocks for testing (`--max-stocks` flag)

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| Import errors | `pip install -r requirements.txt` |
| API keys | Check `.env` file exists |
| Memory errors | Close apps, ensure 16GB RAM |
| Models missing | Run training: `python training/basic_models/{model}/trainer.py` |
| Debug mode | Set `FLASK_DEBUG=True` in `.env` |

## 📚 Additional Resources

See [Main README](../README.md) for overview | [Documentation Hub](../documentation/) for all guides | [Offline Mode](../documentation/OFFLINE_MODE.md) for running without API keys

## ⚠️ Important Notes

- **Model Status**: 4/7 models trained - 3/7 ready for training
- **API Limits**: Finnhub 60 calls/min (free tier), Upstox tokens expire daily
- **Educational Use**: For learning and research only, verify data before financial decisions
- **Offline Mode**: System works without API keys using permanent directory fallback

---

**Version**: 0.1.0 | **Status**: Development (4/7 models trained) | **Updated**: Oct 24, 2025