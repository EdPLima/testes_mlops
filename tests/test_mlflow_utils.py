"""Tests for MLflow utilities"""

import pytest
from unittest.mock import Mock, patch
from src.utils.mlflow_utils import (
    get_latest_model_version,
    get_model_version_by_alias,
    set_model_alias
)


def test_get_latest_model_version():
    """Test getting latest model version"""
    mock_client = Mock()
    mock_version1 = Mock()
    mock_version1.version = "1"
    mock_version2 = Mock()
    mock_version2.version = "2"
    
    mock_client.search_model_versions.return_value = [mock_version1, mock_version2]
    
    result = get_latest_model_version(mock_client, "test_model")
    assert result == 2


def test_get_model_version_by_alias_found():
    """Test getting model version by alias when it exists"""
    mock_client = Mock()
    mock_version = Mock()
    mock_version.version = "5"
    
    mock_client.get_model_version_by_alias.return_value = mock_version
    
    result = get_model_version_by_alias(mock_client, "test_model", "Champion")
    assert result == 5


def test_get_model_version_by_alias_not_found():
    """Test getting model version by alias when it doesn't exist"""
    mock_client = Mock()
    mock_client.get_model_version_by_alias.side_effect = Exception("Not found")
    
    result = get_model_version_by_alias(mock_client, "test_model", "Champion")
    assert result is None
