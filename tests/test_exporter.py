"""Unit tests for Excel report exporter."""
import os
from unittest.mock import MagicMock
import pandas as pd
from google.cloud.bigquery import SchemaField

from src.eda.operators import DescriptionOperator
from src.eda.pipeline import TableWithProcessDict
from src.io.exporter import ExcelReportExporter
from src.models import EDASchemaField, SchemaTable


def test_excel_report_exporter(tmp_path):
    output_path = str(tmp_path / "test_report.xlsx")

    sf = SchemaField("idu_ID", "INTEGER")
    desc = DescriptionOperator.wrapper_select_description_object(sf, DescriptionOperator.select_description_object(sf))
    eda_field = EDASchemaField("idu_ID", "INTEGER", "NULLABLE", desc)

    table = SchemaTable("tbl_1", [eda_field], {}, {"accessibility": True, "num_columns": 1, "num_rows": 10}, "proj.ds.tbl_1")
    item = TableWithProcessDict(table)
    item.metadata["table_page_table_sum"] = pd.DataFrame({"num_columns": [1], "num_rows": [10]})
    item.metadata["table_page_columns_info"] = pd.DataFrame({"Nombre columna": ["idu_ID"], "Tipo": ["INDEX"], "Valores faltantes": [0]})

    exporter = ExcelReportExporter(output_file=output_path)
    res_path = exporter.export([item])

    assert os.path.exists(res_path)
