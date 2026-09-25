from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import pytest
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord, load_raw_records, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks
from pipelines.auto_heal import run_self_healing_pipeline


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def sample_records(settings):
    return load_raw_records(settings.paths.raw_records_json)


@pytest.fixture
def clean_df(sample_records):
    return build_clean_dataframe(sample_records, datetime(2026, 9, 25, tzinfo=UTC))


def test_parse_crossref_payload(settings):
    payload = read_json(settings.paths.raw_api_response)
    records = parse_crossref_payload(payload)
    assert len(records) == 24
    for r in records:
        assert r.paper_id.startswith("10.")
        assert len(r.title) > 0
        assert len(r.summary) > 0
        assert isinstance(r.authors, list)


def test_clean_dataframe(clean_df):
    assert len(clean_df) == 24
    assert clean_df["paper_id"].is_unique
    assert "text_for_embedding" in clean_df.columns
    assert "age_days" in clean_df.columns
    for text in clean_df["text_for_embedding"]:
        assert "Title:" in text
        assert "Authors:" in text
        assert "Summary:" in text


def test_quality_gate_clean_data(clean_df, settings):
    result = run_data_quality_checks(clean_df, settings, "test_clean")
    assert result["success"] is True
    assert result["checks"]["ExpectTableRowCountToBeBetween"] == True
    assert result["checks"]["ExpectColumnValuesToNotBeNull"] == True
    assert result["checks"]["ExpectColumnValuesToBeUnique"] == True
    assert result["checks"]["ExpectColumnValueLengthsToBeBetween"] == True


def test_freshness_sla(clean_df, settings):
    freshness = build_freshness_report(clean_df, settings)
    assert "is_fresh" in freshness
    assert "stale_ratio" in freshness
    assert freshness["total_rows"] == 24


def test_testset_builder(clean_df, tmp_path):
    out_file = tmp_path / "test_set.json"
    test_set = build_test_set(clean_df, out_file)
    assert len(test_set) == 10
    types = {item["question_type"] for item in test_set}
    assert {"summary", "authors", "date", "categories"}.issubset(types)


def test_corruption_suite_triggers_failure(clean_df, settings, tmp_path):
    log_file = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_file)
    assert log_file.exists()
    assert len(corrupted_df) > 0

    # Data Quality Gate should catch the corrupted data (e.g. blank summary or duplicate DOI)
    result = run_data_quality_checks(corrupted_df, settings, "test_corrupted")
    assert result["success"] is False


def test_auto_healing_pipeline(clean_df, tmp_path):
    # Corrupt data then test self-healing
    corrupted = corrupt_clean_dataframe(clean_df, tmp_path / "log.json")
    audit = run_self_healing_pipeline(corrupted, source_label="pytest_run")
    assert audit["action_taken"] == "AUTO_REPAIRED_FROM_RAW"
    assert audit["initial_passed"] is False
    assert audit["repaired_passed"] is True
