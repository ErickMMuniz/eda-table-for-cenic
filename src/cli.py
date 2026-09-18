"""Command line interface entrypoint for EDA processing."""
import argparse
import logging
import sys
from typing import Optional

from src.config.settings import Config
from src.connection.client import BigQueryConnectionManager
from src.eda.pipeline import EDAPipeline
from src.io.exporter import ExcelReportExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract and generate EDA data dictionary report for Google BigQuery datasets."
    )
    default_config = Config()

    parser.add_argument(
        "--project",
        type=str,
        default=default_config.project_id,
        help=f"GCP Project ID (default: {default_config.project_id})",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=default_config.dataset_name,
        help=f"BigQuery Dataset name or ID (default: {default_config.dataset_name})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=default_config.output_file,
        help=f"Output Excel file path (default: {default_config.output_file})",
    )
    return parser


def main(args_list: Optional[list] = None) -> int:
    """Main CLI execution flow."""
    parser = build_parser()
    args = parser.parse_args(args_list)

    config = Config(
        project_id=args.project,
        dataset_name=args.dataset,
        output_file=args.output,
    )

    logger.info("Starting EDA process for dataset '%s' in project '%s'...", config.dataset_id, config.project_id)

    try:
        conn_mgr = BigQueryConnectionManager(project_id=config.project_id)
        client = conn_mgr.get_client()

        pipeline = EDAPipeline(client=client, dataset_id=config.dataset_id, timezone=config.timezone)

        logger.info("Stage 1: Extracting tables and schemas...")
        tables_with_schema = pipeline.run_stage_1_extract_tables_with_schema()
        logger.info("Found %d tables in dataset.", len(tables_with_schema))

        logger.info("Stage 2: Mapping errors and partition columns...")
        tables_with_process = pipeline.run_stage_2_map_errors(tables_with_schema)

        logger.info("Stage 3: Recalculating stats for partitioned tables...")
        tables_with_process = pipeline.run_stage_3_recalculate_partitioned_stats(tables_with_process)

        logger.info("Stage 4: Calculating periodicity...")
        tables_with_process = pipeline.run_stage_4_calculate_periodicity(tables_with_process)

        logger.info("Stage 5: Generating table summaries...")
        tables_with_process = pipeline.run_stage_5_summarize_table_stats(tables_with_process)

        logger.info("Stage 6: Calculating column metrics...")
        tables_with_process = pipeline.run_stage_6_calculate_column_metrics(tables_with_process)

        logger.info("Exporting Excel report to '%s'...", config.output_file)
        exporter = ExcelReportExporter(output_file=config.output_file)
        exporter.export(tables_with_process)

        logger.info("EDA report completed successfully!")
        return 0
    except Exception as e:
        logger.error("EDA process failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
