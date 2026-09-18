"""Unit tests for BigQuery connection manager."""
from unittest.mock import MagicMock, patch
import pytest
from google.auth.exceptions import DefaultCredentialsError

from src.connection.client import BigQueryConnectionManager


@patch("src.connection.client.bigquery.Client")
def test_connection_manager_success(mock_bq_client):
    mock_instance = MagicMock()
    mock_bq_client.return_value = mock_instance

    manager = BigQueryConnectionManager(project_id="test-project")
    client = manager.get_client()

    assert client == mock_instance
    mock_bq_client.assert_called_once_with(project="test-project")


@patch("src.connection.client.bigquery.Client")
def test_connection_manager_adc_error(mock_bq_client):
    mock_bq_client.side_effect = DefaultCredentialsError("ADC error")

    manager = BigQueryConnectionManager(project_id="test-project")
    with pytest.raises(RuntimeError, match="GCP authentication failed"):
        manager.get_client()
