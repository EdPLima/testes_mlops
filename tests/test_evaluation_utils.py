"""Tests for evaluation utilities"""

import pytest
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from src.utils.evaluation_utils import evaluate_model, compare_models


def test_evaluate_model():
    """Test model evaluation"""
    # Create simple dataset
    X_train = pd.DataFrame({'f1': [1, 2, 3, 4], 'f2': [2, 3, 4, 5]})
    y_train = pd.Series([0, 0, 1, 1])
    X_test = pd.DataFrame({'f1': [1.5, 3.5], 'f2': [2.5, 4.5]})
    y_test = pd.Series([0, 1])
    
    # Train model
    model = LogisticRegression(random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test)
    
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1_score' in metrics
    assert 0 <= metrics['accuracy'] <= 1


def test_compare_models():
    """Test model comparison"""
    # Create dataset
    X_train = pd.DataFrame({'f1': [1, 2, 3, 4], 'f2': [2, 3, 4, 5]})
    y_train = pd.Series([0, 0, 1, 1])
    X_test = pd.DataFrame({'f1': [1.5, 3.5], 'f2': [2.5, 4.5]})
    y_test = pd.Series([0, 1])
    
    # Train two models
    model1 = LogisticRegression(random_state=42)
    model1.fit(X_train, y_train)
    
    model2 = LogisticRegression(random_state=43)
    model2.fit(X_train, y_train)
    
    # Compare
    comparison = compare_models(model1, model2, X_test, y_test)
    
    assert 'champion' in comparison
    assert 'challenger' in comparison
    assert 'winner' in comparison
    assert 'improvement' in comparison
    assert comparison['winner'] in ['Champion', 'Challenger']
