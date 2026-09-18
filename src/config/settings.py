"""Application configuration settings."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Holds configuration parameters for BigQuery EDA extraction."""

    project_id: str = "cpl-corp-mpd-prod-01082025"
    dataset_name: str = "mlops_v01_shared"
    dataset_id: Optional[str] = None
    output_file: str = "Data_Dictionary_Report.xlsx"
    timezone: str = "America/Mexico_City"

    def __post_init__(self) -> None:
        if not self.dataset_id and self.project_id and self.dataset_name:
            if "." not in self.dataset_name:
                self.dataset_id = f"{self.project_id}.{self.dataset_name}"
            else:
                self.dataset_id = self.dataset_name
