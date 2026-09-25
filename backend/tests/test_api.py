"""
API Tests for ML Prediction Endpoints

This module tests the Flask API endpoints for ML predictions.
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app, normalize_stock_symbol


@pytest.fixture
def client():
    """Create test client for Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestStockSymbolValidation:
    """Ticker input is normalized before endpoint code uses it."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (" aapl ", "AAPL"),
            ("reliance.ns", "RELIANCE.NS"),
            ("m&m", "M&M"),
            ("mcdowell-n", "MCDOWELL-N"),
        ],
    )
    def test_normalize_stock_symbol(self, raw, expected):
        assert normalize_stock_symbol(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [None, "", "   ", "AA PL", "AAPL/../../etc", "AAPL<script>"],
    )
    def test_normalize_stock_symbol_rejects_invalid_input(self, raw):
        assert normalize_stock_symbol(raw) is None

    @patch("main.get_exchange_rate_info", return_value={"rate": 83.5, "source": "test"})
    @patch("main.live_fetcher.fetch_live_price", return_value={"symbol": "AAPL", "price": 100.0})
    @patch("main.validate_and_categorize_stock", return_value="us_stocks")
    def test_live_price_uses_normalized_symbol(
        self, mock_categorize, mock_fetch, _mock_exchange, client
    ):
        response = client.get("/live_price?symbol=%20aapl%20")

        assert response.status_code == 200
        mock_categorize.assert_called_once_with("AAPL")
        mock_fetch.assert_called_once_with("AAPL")

    @patch("main.live_fetcher.fetch_live_price")
    def test_live_price_rejects_invalid_symbol_before_fetch(self, mock_fetch, client):
        response = client.get("/live_price?symbol=AAPL%2F..")

        assert response.status_code == 400
        mock_fetch.assert_not_called()


class TestPredictionAPI:    """Test cases for prediction API endpoints."""
    
    def test_predict_endpoint_missing_symbol(self, client):
        """Test /api/predict without symbol parameter."""
        response = client.get('/api/predict')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Symbol parameter is required' in data['error']
    
    def test_predict_endpoint_invalid_horizon(self, client):
        """Test /api/predict with invalid horizon."""
        response = client.get('/api/predict?symbol=AAPL&horizon=invalid')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid horizon' in data['error']
    
    def test_predict_endpoint_invalid_model(self, client):
        """Test /api/predict with invalid model."""
        response = client.get('/api/predict?symbol=AAPL&model=invalid')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid model' in data['error']
    
    @patch('algorithms.utils.predict_for_symbol')
    def test_predict_endpoint_success(self, mock_predict, client):
        """Test successful prediction request."""
        # Mock the prediction function
        mock_result = {
            'symbol': 'AAPL',
            'horizon': '1d',
            'predicted_price': 150.25,
            'confidence': 75.5,
            'price_range': [145.0, 155.5],
            'time_frame_days': 1,
            'model_info': {
                'algorithm': 'Ensemble (weighted)',
                'members': ['lstm', 'random_forest'],
                'ensemble_size': 2
            },
            'data_points_used': 1000,
            'last_updated': '2025-01-17T10:00:00Z',
            'currency': 'USD'
        }
        mock_predict.return_value = mock_result
        
        response = client.get('/api/predict?symbol=AAPL&horizon=1d')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['symbol'] == 'AAPL'
        assert data['predicted_price'] == 150.25
        assert data['confidence'] == 75.5
        assert 'model_info' in data
    
    def test_train_endpoint_missing_symbol(self, client):
        """Test /api/train without symbol parameter."""
        response = client.post('/api/train', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Symbol is required' in data['error']
    
    @patch('algorithms.utils.predict_for_symbol')
    def test_train_endpoint_success(self, mock_predict, client):
        """Test successful training request."""
        # Mock the prediction function (which also trains models)
        mock_result = {
            'symbol': 'AAPL',
            'model_info': {
                'members': ['lstm', 'random_forest'],
                'weights': {'lstm': 0.6, 'random_forest': 0.4}
            },
            'data_points_used': 1000,
            'last_updated': '2025-01-17T10:00:00Z'
        }
        mock_predict.return_value = mock_result
        
        response = client.post('/api/train', json={
            'symbol': 'AAPL',
            'models': ['lstm', 'random_forest']
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['symbol'] == 'AAPL'
        assert 'models_trained' in data
        assert 'training_metrics' in data
    
    def test_models_endpoint_no_models(self, client):
        """Test /api/models/<symbol> when no models exist."""
        response = client.get('/api/models/NONEXISTENT')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['symbol'] == 'NONEXISTENT'
        assert data['models'] == []
        assert 'No trained models found' in data['message']
    
    def test_models_endpoint_with_models(self, client):
        """Test /api/models/<symbol> when models exist."""
        # Create a mock models directory structure
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the models directory
            with patch('os.path.join') as mock_join:
                mock_join.side_effect = lambda *args: os.path.join(temp_dir, *args[1:])
                
                # Create mock model directory
                model_dir = os.path.join(temp_dir, 'AAPL', 'lstm_model')
                os.makedirs(model_dir, exist_ok=True)
                
                # Create mock metadata
                metadata = {
                    'saved_at': '2025-01-17T10:00:00Z',
                    'training_metrics': {'rmse': 0.05, 'mae': 0.03},
                    'model_params': {'lookback': 60}
                }
                
                with open(os.path.join(model_dir, 'metadata.json'), 'w') as f:
                    json.dump(metadata, f)
                
                response = client.get('/api/models/AAPL')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['symbol'] == 'AAPL'
                assert len(data['models']) == 1
                assert data['models'][0]['model_name'] == 'lstm_model'


class TestHealthEndpoints:
    """Test cases for health and utility endpoints."""
    
    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data
        assert 'timestamp' in data


if __name__ == '__main__':
    pytest.main([__file__])
