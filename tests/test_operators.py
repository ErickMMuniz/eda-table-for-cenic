"""Unit tests for EDA operators."""
from src.eda.operators import PartitionErrorHelper, PeriodicityOperator
from src.models.enums import EDAPeriodicity


def test_periodicity_operator():
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.001) == EDAPeriodicity.ANUAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.005) == EDAPeriodicity.SEMESTRAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.01) == EDAPeriodicity.TRIMESTRAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.03) == EDAPeriodicity.MENSUAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.1) == EDAPeriodicity.SEMANAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.5) == EDAPeriodicity.DIARIO
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(2.0) == EDAPeriodicity.TRANSACIONAL
    assert PeriodicityOperator.calculate_periodicity_by_year_fraction(0.0) == EDAPeriodicity.SIN_PERIODICIDAD


def test_partition_error_helper():
    error_msg = "Cannot query over table without a filter over column(s) 'fec_FechaCorte' that can be used for partition elimination"
    col = PartitionErrorHelper.get_first_missing_column_for_correct_query(error_msg)
    assert col == "fec_FechaCorte"

    assert PartitionErrorHelper.get_first_missing_column_for_correct_query("Generic error") is None
