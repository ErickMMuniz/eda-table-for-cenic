"""Classification and periodicity operators for EDA fields and tables."""
import re
from typing import Optional
from google.cloud.bigquery import SchemaField as gcpSchemaField

from src.models.enums import EDAPeriodicity, EDATypeDescription
from src.models.schema import (
    CategoricalFieldDescription,
    FieldEDADescription,
    GenericFieldDescription,
    IndexFieldDescription,
    NumericalFieldDescription,
    TemporalFieldDescription,
)


class DescriptionOperator:
    """Selects EDA type descriptions and instantiates FieldEDADescription objects based on field rules."""

    @staticmethod
    def wrapper_select_description_object(
        field: gcpSchemaField, type_desc: EDATypeDescription
    ) -> FieldEDADescription:
        match type_desc:
            case EDATypeDescription.INDEX:
                return IndexFieldDescription(field)
            case EDATypeDescription.NUMERICAL:
                return NumericalFieldDescription(field)
            case EDATypeDescription.CATEGORICAL:
                return CategoricalFieldDescription(field)
            case EDATypeDescription.TEMPORAL:
                return TemporalFieldDescription(field)
            case EDATypeDescription.GENERIC:
                return GenericFieldDescription(field)
            case _:
                raise ValueError(f"Invalid description type: {type_desc}")

    @staticmethod
    def select_description_object(field: gcpSchemaField) -> EDATypeDescription:
        name = field.name
        field_type = field.field_type
        name_lower = name.lower()

        temporal_types = ["TIMESTAMP", "DATE", "DATETIME"]
        if field_type in temporal_types:
            return EDATypeDescription.TEMPORAL
        elif name.startswith("idu") and field_type in ["INTEGER", "STRING"]:
            return EDATypeDescription.INDEX
        elif name.startswith("num") and any(k in name_lower for k in ["cliente", "colaborador", "tienda", "folio"]):
            return EDATypeDescription.INDEX
        elif name.startswith("num") and any(k in name_lower for k in ["anio", "mes", "semana", "hora"]):
            return EDATypeDescription.TEMPORAL
        elif name.startswith("num") and any(
            k in name_lower
            for k in [
                "etapa",
                "tipo",
                "status",
                "nivel",
                "codigo",
                "guia",
                "telefono",
                "lote",
                "empleado",
                "referencia",
            ]
        ):
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("num") and any(k in name_lower for k in ["proveedor", "comprador"]):
            return EDATypeDescription.INDEX
        elif name.startswith("num") and field_type in ["FLOAT", "NUMERIC", "BIGNUMERIC"]:
            return EDATypeDescription.NUMERICAL
        elif name.startswith("nom_") and field_type == "STRING":
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("imp_") and field_type == "STRING":
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("imp_") and field_type in ["INTEGER", "FLOAT", "NUMERIC", "BIGNUMERIC"]:
            return EDATypeDescription.NUMERICAL
        elif name.startswith("id") and "status" in name_lower:
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("id_"):
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("des"):
            return EDATypeDescription.CATEGORICAL
        elif name.startswith("fec"):
            return EDATypeDescription.TEMPORAL
        else:
            return EDATypeDescription.GENERIC


class PeriodicityOperator:
    """Calculates temporal periodicity based on fraction of distinct date values per year."""

    @staticmethod
    def calculate_periodicity_by_year_fraction(year_fraction: float) -> EDAPeriodicity:
        if 0 < year_fraction <= 1 / 365:
            return EDAPeriodicity.ANUAL
        elif 1 / 365 < year_fraction <= 2 / 365:
            return EDAPeriodicity.SEMESTRAL
        elif 2 / 365 < year_fraction <= 4 / 365:
            return EDAPeriodicity.TRIMESTRAL
        elif 4 / 365 < year_fraction <= 12 / 365:
            return EDAPeriodicity.MENSUAL
        elif 12 / 365 < year_fraction <= 52 / 365:
            return EDAPeriodicity.SEMANAL
        elif 52 / 365 < year_fraction <= 1:
            return EDAPeriodicity.DIARIO
        elif year_fraction > 1:
            return EDAPeriodicity.TRANSACIONAL
        else:
            return EDAPeriodicity.SIN_PERIODICIDAD


class PartitionErrorHelper:
    """Extracts required partition/filter column names from BigQuery error messages."""

    @staticmethod
    def get_first_missing_column_for_correct_query(error_str: str) -> Optional[str]:
        pattern = r"over column\(s\)\s+'([^']+)'"
        match = re.search(pattern, error_str)
        return match.group(1) if match else None
