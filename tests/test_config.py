"""Unit tests for Config settings."""
from src.config.settings import Config


def test_config_defaults():
    config = Config()
    assert config.project_id == "cpl-corp-mpd-prod-01082025"
    assert config.dataset_name == "mlops_v01_shared"
    assert config.dataset_id == "cpl-corp-mpd-prod-01082025.mlops_v01_shared"
    assert config.output_file == "Data_Dictionary_Report.xlsx"


def test_config_custom_values():
    config = Config(project_id="my-project", dataset_name="my_dataset", output_file="out.xlsx")
    assert config.dataset_id == "my-project.my_dataset"
    assert config.output_file == "out.xlsx"


def test_config_full_dataset_id():
    config = Config(project_id="my-project", dataset_name="other-project.my_dataset")
    assert config.dataset_id == "other-project.my_dataset"
