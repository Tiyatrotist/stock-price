"""
Unit Tests for Linear Regression Model

Tests covering edge cases for Issue #109:
- Negative target values (percentage returns) don't crash np.log
- Zero variance features
- Regularization variants (Ridge, Lasso, ElasticNet)
- SGD mode with regularization penalties
- Feature importance normalization across model types
- Save/load preserves new parameters
"""

import numpy as np
import os
import sys
import tempfile
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.algorithms.optimised.linear_regression.linear_regression import LinearRegressionModel


# ---------- Fixtures ----------

def _make_positive_data(n_samples=200, n_features=10, seed=42):
    """Create sample data with strictly positive targets (absolute prices)."""
    rng = np.random.RandomState(seed)
    X = rng.randn(n_samples, n_features)
    # Simulate absolute prices (always positive)
    y = 100 + rng.randn(n_samples) * 5  # ~N(100, 5)
    y = np.abs(y) + 1  # Ensure strictly positive
    return X, y


def _make_negative_data(n_samples=200, n_features=10, seed=42):
    """Create sample data with negative targets (percentage returns)."""
    rng = np.random.RandomState(seed)
    X = rng.randn(n_samples, n_features)
    # Simulate percentage returns (can be negative)
    y = rng.randn(n_samples) * 2  # ~N(0, 2), will have negatives
    return X, y


def _make_zero_variance_data(n_samples=200, n_features=10, seed=42):
    """Create data with some zero-variance features."""
    rng = np.random.RandomState(seed)
    X = rng.randn(n_samples, n_features)
    # Set columns 3 and 7 to constant values
    X[:, 3] = 5.0
    X[:, 7] = -2.0
    y = 100 + rng.randn(n_samples) * 5
    y = np.abs(y) + 1
    return X, y


# ---------- Test: Safe log transform ----------

class TestSafeLogTransform:
    """Tests for the np.log(y) crash fix."""

    def test_positive_targets_use_log_transform(self):
        """Positive targets should trigger log transform."""
        X, y = _make_positive_data()
        model = LinearRegressionModel()
        model.fit(X, y)
        assert model.use_log_transform is True
        assert model.training_metrics['log_transformed'] is True

    def test_negative_targets_skip_log_transform(self):
        """Negative targets should skip log transform without crashing."""
        X, y = _make_negative_data()
        model = LinearRegressionModel()
        # This should NOT raise — the old code would crash here with np.log on negatives
        model.fit(X, y)
        assert model.use_log_transform is False
        assert model.training_metrics['log_transformed'] is False

    def test_zero_in_targets_skips_log(self):
        """Targets containing zero should skip log transform."""
        X, y = _make_positive_data()
        y[0] = 0.0  # Insert a zero
        model = LinearRegressionModel()
        model.fit(X, y)
        assert model.use_log_transform is False

    def test_predictions_work_with_negative_targets(self):
        """Model should produce predictions even with negative targets."""
        X, y = _make_negative_data()
        model = LinearRegressionModel()
        model.fit(X, y)
        preds = model.predict(X[:5])
        assert preds.shape == (5,)
        assert not np.any(np.isnan(preds))
        assert not np.any(np.isinf(preds))

    def test_partial_fit_negative_targets(self):
        """SGD partial_fit should handle negative targets safely."""
        X, y = _make_negative_data()
        model = LinearRegressionModel(use_sgd=True)
        model.fit(X, y)
        # partial_fit on a new batch with negatives
        X2, y2 = _make_negative_data(seed=99)
        model.partial_fit(X2, y2)
        assert model.is_trained


# ---------- Test: Regularization variants ----------

class TestRegularization:
    """Tests for Ridge, Lasso, ElasticNet support."""

    def test_default_linear_regression(self):
        """Default model_type='linear' should use plain LinearRegression."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='linear')
        model.fit(X, y)
        assert model.training_metrics['model_type'] == 'linear'
        assert model.training_metrics['alpha'] is None

    def test_ridge_regression(self):
        """model_type='ridge' should use Ridge."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='ridge', alpha=0.5)
        model.fit(X, y)
        assert model.training_metrics['model_type'] == 'ridge'
        assert model.training_metrics['alpha'] == 0.5
        preds = model.predict(X[:5])
        assert preds.shape == (5,)

    def test_lasso_regression(self):
        """model_type='lasso' should use Lasso."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='lasso', alpha=0.1)
        model.fit(X, y)
        assert model.training_metrics['model_type'] == 'lasso'
        preds = model.predict(X[:5])
        assert preds.shape == (5,)

    def test_elasticnet_regression(self):
        """model_type='elasticnet' should use ElasticNet."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='elasticnet', alpha=0.1)
        model.fit(X, y)
        assert model.training_metrics['model_type'] == 'elasticnet'

    def test_sgd_with_l2_penalty(self):
        """SGD mode with model_type='ridge' should set penalty='l2'."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(use_sgd=True, model_type='ridge', alpha=0.01)
        model.fit(X, y)
        assert model.model.penalty == 'l2'
        assert model.is_trained

    def test_sgd_with_l1_penalty(self):
        """SGD mode with model_type='lasso' should set penalty='l1'."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(use_sgd=True, model_type='lasso', alpha=0.01)
        model.fit(X, y)
        assert model.model.penalty == 'l1'

    def test_sgd_with_elasticnet_penalty(self):
        """SGD mode with model_type='elasticnet' should set penalty='elasticnet'."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(use_sgd=True, model_type='elasticnet', alpha=0.01)
        model.fit(X, y)
        assert model.model.penalty == 'elasticnet'

    def test_case_insensitive_model_type(self):
        """model_type should be case-insensitive."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='Ridge')
        model.fit(X, y)
        assert model.model_type == 'ridge'


# ---------- Test: Feature importance ----------

class TestFeatureImportance:
    """Tests for normalized feature importance extraction."""

    def test_feature_importance_without_columns(self):
        """Without feature_columns set, importance should return empty dict."""
        X, y = _make_positive_data()
        model = LinearRegressionModel()
        model.fit(X, y)
        assert model.get_feature_importance() == {}

    def test_feature_importance_with_columns(self):
        """With feature_columns set, importance should return normalized values."""
        X, y = _make_positive_data(n_features=3)
        model = LinearRegressionModel()
        model.fit(X, y)
        model.feature_columns = ['feat_a', 'feat_b', 'feat_c']
        importance = model.get_feature_importance()
        assert len(importance) == 3
        assert set(importance.keys()) == {'feat_a', 'feat_b', 'feat_c'}

    def test_feature_importance_is_normalized(self):
        """Absolute values of normalized coefficients should sum to 1."""
        X, y = _make_positive_data(n_features=5)
        model = LinearRegressionModel()
        model.fit(X, y)
        model.feature_columns = [f'f{i}' for i in range(5)]
        importance = model.get_feature_importance()
        abs_sum = sum(abs(v) for v in importance.values())
        assert abs(abs_sum - 1.0) < 1e-10

    def test_feature_importance_normalized_across_model_types(self):
        """Normalized importance should sum to 1 for all model types."""
        X, y = _make_positive_data(n_features=5)
        for model_type in ['linear', 'ridge', 'lasso']:
            model = LinearRegressionModel(model_type=model_type, alpha=0.01)
            model.fit(X, y)
            model.feature_columns = [f'f{i}' for i in range(5)]
            importance = model.get_feature_importance()
            abs_sum = sum(abs(v) for v in importance.values())
            if abs_sum > 0:  # Lasso can zero out all coefficients
                assert abs(abs_sum - 1.0) < 1e-10, f"Failed for {model_type}"

    def test_feature_importance_sgd(self):
        """SGD model feature importance should also be normalized."""
        X, y = _make_positive_data(n_features=4)
        model = LinearRegressionModel(use_sgd=True)
        model.fit(X, y)
        model.feature_columns = [f'f{i}' for i in range(4)]
        importance = model.get_feature_importance()
        abs_sum = sum(abs(v) for v in importance.values())
        if abs_sum > 0:
            assert abs(abs_sum - 1.0) < 1e-10


# ---------- Test: Zero variance features ----------

class TestZeroVarianceFeatures:
    """Tests for data with zero-variance (constant) features."""

    def test_fit_with_zero_variance_features(self):
        """Model should train without errors even with constant features."""
        X, y = _make_zero_variance_data()
        model = LinearRegressionModel()
        model.fit(X, y)
        assert model.is_trained

    def test_predict_with_zero_variance_features(self):
        """Predictions should not produce NaN/Inf with constant features."""
        X, y = _make_zero_variance_data()
        model = LinearRegressionModel()
        model.fit(X, y)
        preds = model.predict(X[:10])
        assert not np.any(np.isnan(preds))
        assert not np.any(np.isinf(preds))

    def test_ridge_handles_zero_variance(self):
        """Ridge regularization should handle zero-variance features gracefully."""
        X, y = _make_zero_variance_data()
        model = LinearRegressionModel(model_type='ridge', alpha=1.0)
        model.fit(X, y)
        assert model.is_trained
        preds = model.predict(X[:5])
        assert preds.shape == (5,)


# ---------- Test: Save / Load ----------

class TestSaveLoad:
    """Tests that save/load preserves new parameters."""

    def test_save_load_preserves_model_type(self):
        """model_type should survive save/load cycle."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='ridge', alpha=0.5)
        model.fit(X, y)

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            path = f.name

        try:
            model.save(path)
            loaded = LinearRegressionModel()
            loaded.load(path)
            assert loaded.model_type == 'ridge'
            assert loaded.alpha == 0.5
            assert loaded.use_log_transform is True
            assert loaded.is_trained
        finally:
            os.remove(path)

    def test_save_load_preserves_log_transform_flag(self):
        """use_log_transform should survive save/load cycle."""
        X, y = _make_negative_data()
        model = LinearRegressionModel()
        model.fit(X, y)

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            path = f.name

        try:
            model.save(path)
            loaded = LinearRegressionModel()
            loaded.load(path)
            assert loaded.use_log_transform is False
        finally:
            os.remove(path)

    def test_loaded_model_predictions_match(self):
        """Loaded model should produce identical predictions."""
        X, y = _make_positive_data()
        model = LinearRegressionModel(model_type='ridge', alpha=0.1)
        model.fit(X, y)
        original_preds = model.predict(X[:10])

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            path = f.name

        try:
            model.save(path)
            loaded = LinearRegressionModel()
            loaded.load(path)
            loaded_preds = loaded.predict(X[:10])
            np.testing.assert_array_almost_equal(original_preds, loaded_preds)
        finally:
            os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
