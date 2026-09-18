"""Unit tests for CLI main entry point."""
from unittest.mock import MagicMock, patch

from src.cli import main


@patch("src.cli.ExcelReportExporter")
@patch("src.cli.EDAPipeline")
@patch("src.cli.BigQueryConnectionManager")
def test_cli_main_success(mock_conn, mock_pipe_cls, mock_exp_cls):
    mock_client = MagicMock()
    mock_conn.return_value.get_client.return_value = mock_client

    mock_pipeline = MagicMock()
    mock_pipe_cls.return_value = mock_pipeline
    mock_pipeline.run_stage_1_extract_tables_with_schema.return_value = []
    mock_pipeline.run_stage_2_map_errors.return_value = []
    mock_pipeline.run_stage_3_recalculate_partitioned_stats.return_value = []
    mock_pipeline.run_stage_4_calculate_periodicity.return_value = []
    mock_pipeline.run_stage_5_summarize_table_stats.return_value = []
    mock_pipeline.run_stage_6_calculate_column_metrics.return_value = []

    exit_code = main(["--project", "test-proj", "--dataset", "test_ds", "--output", "out.xlsx"])
    assert exit_code == 0
    mock_exp_cls.assert_called_once_with(output_file="out.xlsx")
