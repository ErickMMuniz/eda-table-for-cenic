"""Domain models for EDA Schema representations."""
from abc import ABC, abstractmethod
from functools import reduce
from typing import Any, Dict, List, Optional
from google.cloud.bigquery import SchemaField as gcpSchemaField

from src.models.enums import EDATypeDescription


class FieldEDADescription(ABC):
    """Abstract base class for field-level EDA descriptions."""

    def __init__(self, field_schema: gcpSchemaField):
        self._name = field_schema.name
        self._field_type = field_schema.field_type
        self._mode = field_schema.mode

    @property
    def name(self) -> str:
        return self._name

    @property
    def field_type(self) -> str:
        return self._field_type

    @property
    def mode(self) -> str:
        return self._mode

    @property
    @abstractmethod
    def type_description(self) -> EDATypeDescription:
        """Returns the type description enum for the field."""
        pass

    @abstractmethod
    def generate_calculation(self) -> Dict[str, str]:
        """Generates SQL aggregation expressions for metric calculations."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Converts instance to dictionary format."""
        return {
            "name": self._name,
            "field_type": self._field_type,
            "mode": self._mode,
            "type_description": self.type_description.value,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', type_description='{self.type_description.value}')"


class IndexFieldDescription(FieldEDADescription):
    """EDA description for index key fields."""

    @property
    def type_description(self) -> EDATypeDescription:
        return EDATypeDescription.INDEX

    def generate_calculation(self) -> Dict[str, str]:
        return {
            f"{self._name}_missing_values": f"SUM(CASE WHEN {self._name} IS NULL THEN 1 ELSE 0 END)",
            f"{self._name}_unique_values": f"COUNT(DISTINCT {self._name})",
            f"{self._name}_count_values": f"COUNT({self._name})",
        }


class NumericalFieldDescription(FieldEDADescription):
    """EDA description for numerical fields."""

    @property
    def type_description(self) -> EDATypeDescription:
        return EDATypeDescription.NUMERICAL

    def generate_calculation(self) -> Dict[str, str]:
        return {
            f"{self._name}_missing_values": f"SUM(CASE WHEN {self._name} IS NULL THEN 1 ELSE 0 END)",
            f"{self._name}_min_value": f"MIN({self._name})",
            f"{self._name}_max_value": f"MAX({self._name})",
            f"{self._name}_mean_value": f"AVG({self._name})",
            f"{self._name}_std_value": f"STDDEV({self._name})",
            f"{self._name}_count_values": f"COUNT({self._name})",
        }


class CategoricalFieldDescription(FieldEDADescription):
    """EDA description for categorical fields."""

    @property
    def type_description(self) -> EDATypeDescription:
        return EDATypeDescription.CATEGORICAL

    def generate_calculation(self) -> Dict[str, str]:
        return {
            f"{self._name}_missing_values": f"SUM(CASE WHEN {self._name} IS NULL THEN 1 ELSE 0 END)",
            f"{self._name}_count_values": f"COUNT({self._name})",
            f"{self._name}_unique_values": f"COUNT(DISTINCT {self._name})",
        }


class TemporalFieldDescription(FieldEDADescription):
    """EDA description for temporal date/timestamp fields."""

    @property
    def type_description(self) -> EDATypeDescription:
        return EDATypeDescription.TEMPORAL

    def generate_calculation(self) -> Dict[str, str]:
        return {
            f"{self._name}_missing_values": f"SUM(CASE WHEN {self._name} IS NULL THEN 1 ELSE 0 END)",
            f"{self._name}_min_value": f"MIN({self._name})",
            f"{self._name}_max_value": f"MAX({self._name})",
        }


class GenericFieldDescription(FieldEDADescription):
    """EDA description for generic/unclassified fields."""

    @property
    def type_description(self) -> EDATypeDescription:
        return EDATypeDescription.GENERIC

    def generate_calculation(self) -> Dict[str, str]:
        return {
            f"{self._name}_missing_values": f"SUM(CASE WHEN {self._name} IS NULL THEN 1 ELSE 0 END)",
            f"{self._name}_count_values": f"COUNT({self._name})",
        }


class EDASchemaField:
    """Represents a schema field with metadata and EDA calculation rules."""

    def __init__(
        self,
        name: str,
        field_type: str,
        mode: str,
        eda_description: FieldEDADescription,
        description: Optional[str] = None,
    ):
        self.name = name
        self.field_type = field_type
        self.mode = mode
        self.description = description
        self.eda_description = eda_description

    def generate_calculation(self) -> Dict[str, str]:
        return self.eda_description.generate_calculation()

    def __repr__(self) -> str:
        return (
            f"EDASchemaField(name='{self.name}', type='{self.field_type}', "
            f"mode='{self.mode}', eda_description={self.eda_description})"
        )


class SchemaTable:
    """Represents a BigQuery table schema and metric calculation queries."""

    def __init__(
        self,
        name: str,
        fields: List[EDASchemaField],
        error: Dict[str, Any],
        stats: Dict[str, Any],
        table_id: str,
    ):
        self.name = name
        self.fields = fields
        self.error = error
        self.stats = stats
        self.table_id = table_id

    def generate_query(self) -> str:
        """Generates SQL query combining metric calculations for all schema fields."""
        calculations_list = [field.generate_calculation() for field in self.fields]
        combined_calc: Dict[str, str] = reduce(lambda a, b: {**a, **b}, calculations_list, {})

        if not combined_calc:
            return f"SELECT 1 FROM `{self.table_id}` LIMIT 0"

        param_expressions = [f"  {value} AS {key}" for key, value in combined_calc.items()]
        query_params = ",\n".join(param_expressions)

        query_base = f"""SELECT
{query_params}
FROM
  `{self.table_id}`"""
        return query_base

    def __repr__(self) -> str:
        return f"SchemaTable(name='{self.name}', fields_count={len(self.fields)})"
