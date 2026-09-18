"""BigQuery connection initialization using GCP Application Default Credentials (ADC)."""
import logging
from typing import Optional
from google.cloud import bigquery
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)


class BigQueryConnectionManager:
    """Manages creation and lifecycle of Google Cloud BigQuery client."""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id
        self._client: Optional[bigquery.Client] = None

    def get_client(self) -> bigquery.Client:
        """Returns initialized BigQuery client using ADC.

        Raises:
            RuntimeError: If authentication fails or credentials are missing.
        """
        if self._client is None:
            try:
                self._client = bigquery.Client(project=self.project_id)
                logger.info("Successfully initialized BigQuery client for project: '%s'", self.project_id)
            except DefaultCredentialsError as e:
                logger.error("GCP Application Default Credentials (ADC) not found.")
                raise RuntimeError(
                    "GCP authentication failed. Please run 'gcloud auth application-default login' "
                    "or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
                ) from e
            except Exception as e:
                logger.error("Failed to initialize BigQuery client: %s", e)
                raise RuntimeError(f"Error initializing BigQuery client: {e}") from e
        return self._client
