"""Unit tests for domain models and field descriptions."""
from unittest.mock import MagicMock
from google.cloud.bigquery import SchemaField

from src.eda.operators import DescriptionOperator
from src.models import (
    CategoricalFieldDescription,
    EDASchemaField,
    EDATypeDescription,
    IndexFieldDescription,
    NumericalFieldDescription,
    SchemaTable,
    TemporalFieldDescription,
)


def test_description_operator_classification():
    field_fec = SchemaField("fec_FechaCorte", "DATE")
    field_id = SchemaField("idu_Cliente", "INTEGER")
    field_num = SchemaField("num_Monto", "FLOAT")
    field_nom = SchemaField("nom_Persona", "STRING")

    assert DescriptionOperator.select_description_object(field_fec) == EDATypeDescription.TEMPORAL
    assert DescriptionOperator.select_description_object(field_id) == EDATypeDescription.INDEX
    assert DescriptionOperator.select_description_object(field_num) == EDATypeDescription.NUMERICAL
    assert DescriptionOperator.select_description_object(field_nom) == EDATypeDescription.CATEGORICAL


def test_schema_field_and_table_query_generation():
    field_num_sf = SchemaField("num_Monto", "FLOAT")
    num_desc = NumericalFieldDescription(field_num_sf)
    eda_field = EDASchemaField(
        name="num_Monto",
        field_type="FLOAT",
        mode="NULLABLE",
        eda_description=num_desc,
    )

    table = SchemaTable(
        name="test_table",
        fields=[eda_field],
        error={},
        stats={"accessibility": True},
        table_id="proj.dataset.test_table",
    )

    query = table.generate_query()
    assert "SELECT" in query
    assert "num_Monto_missing_values" in query
    assert "FROM" in query
    assert "`proj.dataset.test_table`" in query
