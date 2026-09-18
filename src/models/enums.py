"""Enum definitions for EDA and Periodicity types."""
from enum import Enum
from typing import List


class EDATypeDescription(Enum):
    """Enumeration for Exploratory Data Analysis (EDA) field description types."""

    INDEX = "INDEX"
    NUMERICAL = "NUMERICAL"
    CATEGORICAL = "CATEGORICAL"
    TEMPORAL = "TEMPORAL"
    GENERIC = "GENERIC"

    @classmethod
    def list_values(cls) -> List[str]:
        """Returns list of all enum member values."""
        return [member.value for member in cls]


class EDAPeriodicity(Enum):
    """Enumeration for table temporal periodicity."""

    ANUAL = "ANUAL"
    SEMESTRAL = "SEMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    MENSUAL = "MENSUAL"
    SEMANAL = "SEMANAL"
    DIARIO = "DIARIO"
    TRANSACIONAL = "TRANSACIONAL"
    SIN_PERIODICIDAD = "SIN_PERIODICIDAD"
