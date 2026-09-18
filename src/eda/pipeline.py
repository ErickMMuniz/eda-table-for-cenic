"""EDA processing pipeline orchestrator."""
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from google.cloud import bigquery

from src.eda.operators import DescriptionOperator, PartitionErrorHelper, PeriodicityOperator
from src.models.enums import EDAPeriodicity, EDATypeDescription
from src.models.schema import EDASchemaField, SchemaTable

logger = logging.getLogger(__name__)


class TableWithProcessDict:
    """Wrapper holding a SchemaTable and its processing metadata/logs."""

    def __init__(self, table: SchemaTable):
        self.table = table
        self.process: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}


class EDAPipeline:
    """Orchestrates multi-stage EDA analysis on BigQuery dataset tables."""

    def __init__(self, client: bigquery.Client, dataset_id: str, timezone: str = "America/Mexico_City"):
        self.client = client
        self.dataset_id = dataset_id
        self.timezone = timezone

    def run_stage_1_extract_tables_with_schema(self) -> List[SchemaTable]:
        """Stage 1: List dataset tables and inspect basic schema and table metrics."""
        tables = list(self.client.list_tables(self.dataset_id))
        tables_with_schema: List[SchemaTable] = []

        for table in tables:
            table_ref = f"{self.dataset_id}.{table.table_id}"
            try:
                full_table = self.client.get_table(table_ref)
            except Exception as e:
                logger.error("Error fetching table metadata for %s: %s", table_ref, e)
                continue

            stats_table: Dict[str, Any] = {}
            error_table: Dict[str, Any] = {}
            elements_table: List[EDASchemaField] = []

            query = f"""
WITH
ColumnInfo AS (
  SELECT COUNT(*) AS numero_de_columnas
  FROM `{self.dataset_id}.INFORMATION_SCHEMA.COLUMNS`
  WHERE table_name = '{table.table_id}'
),
RowInfo AS (
  SELECT COUNT(*) AS numero_de_filas
  FROM `{self.dataset_id}.{table.table_id}`
),
CreationTime AS (
  SELECT creation_time
  FROM `{self.dataset_id}.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = '{table.table_id}'
)
SELECT
  ColumnInfo.numero_de_columnas as num_columns,
  RowInfo.numero_de_filas as num_rows,
  CreationTime.creation_time as creation_time
FROM ColumnInfo, RowInfo, CreationTime;
"""
            try:
                tables_stats_df = self.client.query(query).to_dataframe()
                stats_table["accessibility"] = True
                stats_table["num_columns"] = int(tables_stats_df["num_columns"][0])
                stats_table["num_rows"] = int(tables_stats_df["num_rows"][0])
                creation_date_utc = tables_stats_df["creation_time"][0]
                creation_date_local = creation_date_utc.tz_convert(self.timezone)
                stats_table["creation_time"] = creation_date_local.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.warning("Query error on table %s: %s", table_ref, e)
                error_table["missing_query"] = str(e)
                stats_table["accessibility"] = False
                stats_table["num_columns"] = None
                stats_table["num_rows"] = None

            if full_table.schema:
                for field in full_table.schema:
                    type_field = DescriptionOperator.select_description_object(field)
                    description_wrapper = DescriptionOperator.wrapper_select_description_object(field, type_field)
                    eda_schema_field = EDASchemaField(
                        name=field.name,
                        field_type=field.field_type,
                        mode=field.mode,
                        eda_description=description_wrapper,
                        description=field.description,
                    )
                    elements_table.append(eda_schema_field)

            schema_table = SchemaTable(
                name=table.table_id,
                fields=elements_table,
                error=error_table,
                stats=stats_table,
                table_id=table_ref,
            )
            tables_with_schema.append(schema_table)

        return tables_with_schema

    def run_stage_2_map_errors(self, tables_with_schema: List[SchemaTable]) -> List[TableWithProcessDict]:
        """Stage 2: Map error logs and identify partition column for required query filters."""
        tables_with_process = [TableWithProcessDict(t) for t in tables_with_schema]

        for item in tables_with_process:
            if not item.table.error:
                item.process["first_process_log"] = "No errors"
            else:
                error_str = str(item.table.error.get("missing_query", ""))
                item.process["first_process_log"] = error_str
                if "reason: invalidQuery, location: query" in error_str:
                    col_name = PartitionErrorHelper.get_first_missing_column_for_correct_query(error_str)
                    item.metadata["periodicity_column_name"] = col_name

        return tables_with_process

    def run_stage_3_recalculate_partitioned_stats(
        self, tables_with_process: List[TableWithProcessDict]
    ) -> List[TableWithProcessDict]:
        """Stage 3: Retry stats query for partitioned tables using a standard 1-year interval filter."""
        for item in tables_with_process:
            if item.table.error and "reason: invalidQuery, location: query" in item.process.get("first_process_log", ""):
                missing_col = PartitionErrorHelper.get_first_missing_column_for_correct_query(
                    item.table.error["missing_query"]
                )
                if not missing_col:
                    continue

                query = f"""
WITH ColumnInfo AS (
  SELECT COUNT(*) AS numero_de_columnas
  FROM `{self.dataset_id}.INFORMATION_SCHEMA.COLUMNS`
  WHERE table_name = '{item.table.name}'
),
RowInfo AS (
  SELECT COUNT(*) AS numero_de_filas
  FROM `{self.dataset_id}.{item.table.name}`
  WHERE {missing_col} > (CURRENT_DATE - INTERVAL 1 year)
),
CreationTime AS (
  SELECT creation_time
  FROM `{self.dataset_id}.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = '{item.table.name}'
)
SELECT
  ColumnInfo.numero_de_columnas as num_columns,
  RowInfo.numero_de_filas as num_rows,
  CreationTime.creation_time as creation_time
FROM ColumnInfo, RowInfo, CreationTime;
"""
                try:
                    tables_stats_df = self.client.query(query).to_dataframe()
                    item.table.stats["num_columns"] = int(tables_stats_df["num_columns"][0])
                    item.table.stats["num_rows"] = int(tables_stats_df["num_rows"][0])
                    creation_date_utc = tables_stats_df["creation_time"][0]
                    creation_date_local = creation_date_utc.tz_convert(self.timezone)
                    item.table.stats["creation_time"] = creation_date_local.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    logger.warning("Retry stats failed for %s: %s", item.table.table_id, e)

        return tables_with_process

    def run_stage_4_calculate_periodicity(
        self, tables_with_process: List[TableWithProcessDict]
    ) -> List[TableWithProcessDict]:
        """Stage 4: Calculate temporal periodicity for partitioned and non-partitioned tables."""
        for item in tables_with_process:
            if "periodicity_column_name" not in item.metadata or not item.metadata["periodicity_column_name"]:
                temporal_fields = [
                    f for f in item.table.fields if f.eda_description.type_description == EDATypeDescription.TEMPORAL
                ]
                if temporal_fields:
                    possible_names = [f.name for f in temporal_fields]
                    prefer_words = [
                        "facturacion",
                        "particion",
                        "actualizacion",
                        "corte",
                        "movimiento",
                        "fechasql",
                        "solicitud",
                        "fec",
                    ]
                    sorted_names = sorted(
                        possible_names,
                        key=lambda x: sum(x.lower().count(w) for w in prefer_words),
                        reverse=True,
                    )
                    item.metadata["periodicity_column_name"] = sorted_names[0]
                else:
                    item.metadata["periodicity_column_name"] = None

            missing_col = item.metadata.get("periodicity_column_name")
            if missing_col:
                query = f"""
SELECT COUNT(DISTINCT {missing_col}) as count_distinct_values
FROM `{item.table.table_id}`
WHERE {missing_col} > (CURRENT_DATE - INTERVAL 1 YEAR);
"""
                try:
                    distinct_val = float(self.client.query(query).to_dataframe()["count_distinct_values"][0])
                    year_fraction = distinct_val / 365.0
                    periodicity = PeriodicityOperator.calculate_periodicity_by_year_fraction(year_fraction)
                    item.metadata["periodicity"] = periodicity
                    item.table.stats["periodicity"] = periodicity.value
                except Exception as e:
                    logger.warning("Periodicity query failed for %s: %s", item.table.table_id, e)
                    item.metadata["periodicity"] = EDAPeriodicity.SIN_PERIODICIDAD
                    item.table.stats["periodicity"] = EDAPeriodicity.SIN_PERIODICIDAD.value
            else:
                item.metadata["periodicity"] = EDAPeriodicity.SIN_PERIODICIDAD
                item.table.stats["periodicity"] = EDAPeriodicity.SIN_PERIODICIDAD.value

        return tables_with_process

    def run_stage_5_summarize_table_stats(
        self, tables_with_process: List[TableWithProcessDict]
    ) -> List[TableWithProcessDict]:
        """Stage 5: Generate tabular summary dataframes for each table."""
        for item in tables_with_process:
            item.metadata["table_page_name"] = item.table.table_id
            df_summary = pd.DataFrame(item.table.stats, index=[0])
            readable_cols = {
                "num_columns": "Número de columnas",
                "num_rows": "Número de filas",
                "creation_time": "Fecha de creación",
                "accessibility": "Accesibilidad",
                "periodicity": "Periodicidad",
            }
            df_summary.rename(columns=readable_cols, inplace=True)
            if "periodicity_column_name" in item.metadata:
                df_summary["Columna de periodicidad"] = item.metadata["periodicity_column_name"]
            item.metadata["table_page_table_sum"] = df_summary

        return tables_with_process

    def run_stage_6_calculate_column_metrics(
        self, tables_with_process: List[TableWithProcessDict]
    ) -> List[TableWithProcessDict]:
        """Stage 6: Execute field metric calculation query per table and construct column metadata dataframes."""
        for item in tables_with_process:
            is_valid = item.table.stats.get("accessibility", False)
            if not is_valid:
                df_field_info = pd.DataFrame(
                    {
                        "Nombre columna": [f.name for f in item.table.fields],
                        "Tipo": [f.eda_description.type_description.value for f in item.table.fields],
                    }
                )
                item.metadata["table_page_columns_info"] = df_field_info
            else:
                try:
                    query_data_columns = item.table.generate_query()
                    df_cols_info = self.client.query(query_data_columns).to_dataframe()

                    list_data_columns = []
                    for field in item.table.fields:
                        name = field.name
                        type_field = field.eda_description.type_description.value
                        info_column: Dict[str, Any] = {"name": name, "type": type_field}

                        valid_cols = [c for c in df_cols_info.columns if c.startswith(name)]
                        for valid_col in valid_cols:
                            val = df_cols_info[valid_col][0]
                            if "missing_values" in valid_col:
                                info_column["missing_values"] = int(val) if pd.notna(val) else 0
                            elif "count_values" in valid_col:
                                info_column["count_values"] = int(val) if pd.notna(val) else 0
                            elif "min_value" in valid_col:
                                info_column["min_value"] = val
                            elif "max_value" in valid_col:
                                info_column["max_value"] = val
                            elif "unique_values" in valid_col:
                                info_column["unique_values"] = int(val) if pd.notna(val) else 0
                            elif "std_value" in valid_col:
                                info_column["std_value"] = float(val) if pd.notna(val) else None
                            elif "mean_value" in valid_col:
                                info_column["mean_value"] = float(val) if pd.notna(val) else None

                        list_data_columns.append(info_column)

                    df_cols = pd.DataFrame(list_data_columns)
                    rename_dict = {
                        "name": "Nombre columna",
                        "type": "Tipo",
                        "missing_values": "Valores faltantes",
                        "unique_values": "Valores únicos",
                        "count_values": "Conteo de valores",
                        "min_value": "Valor mínimo",
                        "max_value": "Valor máximo",
                        "mean_value": "Media",
                        "std_value": "Desviación estándar",
                    }
                    df_cols.rename(columns=rename_dict, inplace=True)
                    num_rows = item.table.stats.get("num_rows")
                    if num_rows and "Valores faltantes" in df_cols.columns:
                        df_cols["Porcentaje de valores faltantes"] = (
                            df_cols["Valores faltantes"] / float(num_rows)
                        ).round(2)

                    item.metadata["table_page_columns_info"] = df_cols
                except Exception as e:
                    logger.warning("Error calculating column metrics for %s: %s", item.table.table_id, e)
                    item.metadata["table_page_columns_info"] = pd.DataFrame(
                        {
                            "Nombre columna": [f.name for f in item.table.fields],
                            "Tipo": [f.eda_description.type_description.value for f in item.table.fields],
                        }
                    )

        return tables_with_process
