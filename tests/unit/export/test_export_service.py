from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.export import ExportService
from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.models import (
    CandidateId,
    GoldRecord,
    GoldRecordId,
    NormalizedRecord,
    NormalizedValue,
    RawRecord,
)
from mod_personnel_db.repositories import GoldRepository
from mod_personnel_db.utils.exceptions import RepositoryError

from ._stubs import StubGoldRepository


def _make_normalized_record() -> NormalizedRecord:
    raw = RawRecord(
        section_ref=None,
        layout_id="reiwa",
        record_index=0,
        raw_fields={"rank": "大将?"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_gold_record(
    record_id: int,
    person_key: str,
    is_current: bool = True,
    effective_date: date = date(2026, 1, 1),
) -> GoldRecord:
    return GoldRecord(
        id=GoldRecordId(record_id),
        candidate_id=CandidateId(1),
        person_key=person_key,
        effective_date=effective_date,
        appointment_type="promotion",
        fields=_make_normalized_record(),
        version=1,
        is_current=is_current,
        superseded_by=None,
    )


def test_export_all_returns_current_gold_records() -> None:
    current = _make_gold_record(1, "person-1")
    superseded = _make_gold_record(2, "person-2", is_current=False)
    repository = StubGoldRepository(records=(current, superseded))
    service = RepositoryExportService(repository)

    result = service.export_all()

    assert result == (current,)
    assert repository.list_current_calls == [None]


def test_export_since_passes_as_of_to_repository() -> None:
    record = _make_gold_record(1, "person-1")
    repository = StubGoldRepository(records=(record,))
    service = RepositoryExportService(repository)
    since = datetime(2026, 6, 1, tzinfo=UTC)

    result = service.export_since(since)

    assert result == (record,)
    assert repository.list_current_calls == [since]


def test_export_person_returns_history_for_person_key() -> None:
    person_a = _make_gold_record(1, "person-a")
    person_b = _make_gold_record(2, "person-b")
    repository = StubGoldRepository(records=(person_a, person_b))
    service = RepositoryExportService(repository)

    result = service.export_person("person-a")

    assert result == (person_a,)
    assert repository.get_history_calls == ["person-a"]


def test_export_person_returns_empty_tuple_for_unknown_person() -> None:
    repository = StubGoldRepository(records=(_make_gold_record(1, "person-a"),))
    service = RepositoryExportService(repository)

    result = service.export_person("unknown-person")

    assert result == ()


def test_export_all_delegates_only_to_gold_repository() -> None:
    repository = StubGoldRepository(records=(_make_gold_record(1, "person-1"),))
    service = RepositoryExportService(repository)

    service.export_all()

    assert repository.get_history_calls == []


def test_repository_error_propagates_unwrapped_from_export_all() -> None:
    repository = StubGoldRepository(raise_on="list_current")
    service = RepositoryExportService(repository)

    with pytest.raises(RepositoryError):
        service.export_all()


def test_repository_error_propagates_unwrapped_from_export_person() -> None:
    repository = StubGoldRepository(raise_on="get_history")
    service = RepositoryExportService(repository)

    with pytest.raises(RepositoryError):
        service.export_person("person-1")


def test_export_service_satisfies_protocol() -> None:
    typed_repository: GoldRepository = StubGoldRepository(
        records=(_make_gold_record(1, "person-1"),)
    )
    service: ExportService = RepositoryExportService(typed_repository)

    assert service.export_all() != ()
    assert service.export_since(datetime(2026, 1, 1, tzinfo=UTC)) != ()
    assert service.export_person("person-1") != ()


def test_export_service_public_api_matches_protocol() -> None:
    public_names = {name for name in dir(RepositoryExportService) if not name.startswith("_")}

    assert public_names == {"export_all", "export_since", "export_person"}
