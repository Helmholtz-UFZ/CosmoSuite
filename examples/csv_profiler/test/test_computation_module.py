"""Unit tests for the CSV statistical profiler (computation_module.py)."""

import os

import pandas as pd
import pytest

from csv_profiler.computation_module import profile_csv


@pytest.fixture
def sample_mixed_csv():
    """Path to the sample mixed CSV in the test directory."""
    return os.path.join(os.path.dirname(__file__), "sample_mixed.csv")


@pytest.fixture
def numeric_only_csv(tmp_path):
    """Create a CSV with only numeric columns."""
    df = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [10, 20, 30, 40, 50],
            "c": [100, 200, 300, 400, 500],
        }
    )
    path = str(tmp_path / "numeric.csv")
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def categorical_only_csv(tmp_path):
    """Create a CSV with only categorical columns."""
    df = pd.DataFrame(
        {
            "color": ["red", "blue", "green", "red", "blue", "red"],
            "size": ["S", "M", "L", "M", "S", "L"],
            "shape": ["circle", "square", "circle", "triangle", "circle", "square"],
        }
    )
    path = str(tmp_path / "categorical.csv")
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def csv_with_missing(tmp_path):
    """Create a CSV with missing values."""
    df = pd.DataFrame(
        {
            "x": [1.0, None, 3.0, None, 5.0],
            "y": [10.0, 20.0, None, 40.0, 50.0],
            "label": ["a", None, "c", "a", None],
        }
    )
    path = str(tmp_path / "missing.csv")
    df.to_csv(path, index=False)
    return path


class TestProfileCsvNumericOnly:
    def test_structure(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv)
        assert result["row_count"] == 5
        assert result["column_count"] == 3
        assert "a" in result["summary"]
        assert "b" in result["summary"]
        assert "c" in result["summary"]

    def test_numeric_stats(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv)
        a = result["summary"]["a"]
        assert a["dtype"] == "numeric"
        assert a["mean"] == 3.0
        assert a["min"] == 1.0
        assert a["max"] == 5.0
        assert a["count"] == 5

    def test_histograms_present(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv, histogram_bins=5)
        assert "a" in result["histograms"]
        assert len(result["histograms"]["a"]["values"]) == 5
        assert len(result["histograms"]["a"]["bin_edges"]) == 6

    def test_correlation_matrix(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv)
        corr = result["correlation_matrix"]
        assert "columns" in corr
        assert len(corr["columns"]) == 3
        assert len(corr["values"]) == 3
        # Perfect correlation between a, b, c (all linear)
        assert corr["values"][0][0] == pytest.approx(1.0)

    def test_no_value_counts(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv)
        assert result["value_counts"] == {}


class TestProfileCsvCategoricalOnly:
    def test_structure(self, categorical_only_csv):
        result = profile_csv(categorical_only_csv)
        assert result["row_count"] == 6
        assert result["column_count"] == 3

    def test_categorical_stats(self, categorical_only_csv):
        result = profile_csv(categorical_only_csv)
        color = result["summary"]["color"]
        assert color["dtype"] == "categorical"
        assert color["unique"] == 3
        assert color["most_common"] == "red"
        assert color["most_common_count"] == 3

    def test_value_counts(self, categorical_only_csv):
        result = profile_csv(categorical_only_csv)
        assert "color" in result["value_counts"]
        assert result["value_counts"]["color"]["red"] == 3

    def test_no_correlation(self, categorical_only_csv):
        result = profile_csv(categorical_only_csv)
        assert result["correlation_matrix"] == {}

    def test_no_histograms(self, categorical_only_csv):
        result = profile_csv(categorical_only_csv)
        assert result["histograms"] == {}


class TestProfileCsvMixed:
    def test_mixed_csv(self, sample_mixed_csv):
        result = profile_csv(sample_mixed_csv)
        assert result["row_count"] == 30
        assert result["column_count"] == 7
        # Numeric columns
        assert result["summary"]["age"]["dtype"] == "numeric"
        assert result["summary"]["salary"]["dtype"] == "numeric"
        assert result["summary"]["score"]["dtype"] == "numeric"
        # Categorical columns
        assert result["summary"]["name"]["dtype"] == "categorical"
        assert result["summary"]["department"]["dtype"] == "categorical"
        assert result["summary"]["city"]["dtype"] == "categorical"
        assert result["summary"]["rating"]["dtype"] == "categorical"


class TestMissingValueHandling:
    def test_drop(self, csv_with_missing):
        result = profile_csv(csv_with_missing, handle_missing="drop")
        # dropna() drops rows with any NaN across numeric cols (x and y),
        # rows 1(x=NaN), 2(y=NaN), 3(x=NaN) dropped → rows 0,4 remain
        assert result["summary"]["x"]["count"] == 2

    def test_fill_mean(self, csv_with_missing):
        result = profile_csv(csv_with_missing, handle_missing="fill_mean")
        assert result["summary"]["x"]["count"] == 5

    def test_fill_zero(self, csv_with_missing):
        result = profile_csv(csv_with_missing, handle_missing="fill_zero")
        assert result["summary"]["x"]["count"] == 5
        # Mean should be lower because NaN replaced with 0
        assert result["summary"]["x"]["mean"] == pytest.approx(1.8)

    def test_keep(self, csv_with_missing):
        result = profile_csv(csv_with_missing, handle_missing="keep")
        # count should still be 3 (NaN not counted by pandas)
        assert result["summary"]["x"]["count"] == 3

    def test_missing_values_reported(self, csv_with_missing):
        result = profile_csv(csv_with_missing)
        assert result["missing_values"]["x"]["count"] == 2
        assert result["missing_values"]["x"]["percent"] == 40.0
        assert result["missing_values"]["label"]["count"] == 2


class TestColumnSelection:
    def test_select_subset(self, sample_mixed_csv):
        result = profile_csv(sample_mixed_csv, columns=["age", "name"])
        assert result["column_count"] == 2
        assert "age" in result["summary"]
        assert "name" in result["summary"]
        assert "salary" not in result["summary"]

    def test_nonexistent_column_skipped(self, sample_mixed_csv):
        result = profile_csv(sample_mixed_csv, columns=["age", "nonexistent"])
        assert result["column_count"] == 1
        assert "age" in result["summary"]


class TestCorrelationToggle:
    def test_correlation_disabled(self, numeric_only_csv):
        result = profile_csv(numeric_only_csv, compute_correlation=False)
        assert result["correlation_matrix"] == {}

    def test_correlation_needs_two_numeric(self, csv_with_missing):
        result = profile_csv(csv_with_missing, columns=["x"])
        # Only one numeric column — no correlation
        assert result["correlation_matrix"] == {}
