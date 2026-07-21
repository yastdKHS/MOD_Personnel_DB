"""JobRunnerテスト専用のStub群。具象実装はsrc/には置かない（Phase3 Task10-1, Task10-4）。"""

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import cast

from mod_personnel_db.models import (
    CandidateId,
    CandidateRecord,
    Confidence,
    ConfidenceBand,
    FieldExtractionResult,
    Job,
    JobId,
    KnowledgeItem,
    KnowledgeSnapshot,
    LearningRecord,
    LearningRecordId,
    NormalizationResult,
    NormalizedRecord,
    NormalizedValue,
    ParserVersion,
    ParserVersionId,
    PdfId,
    PdfRecord,
    PersonnelSection,
    PersonnelSectionId,
    RawRecord,
    SectionParseResult,
    ValidationCandidate,
    ValidationEvidence,
    ValidationResult,
    ValidationRuleSet,
)
from mod_personnel_db.pipeline.exceptions import PipelineException

_DEFAULT_AS_OF = date(2026, 1, 1)
_CONFIDENCE = Confidence(score=1.0, band=ConfidenceBand.VERIFIED)


def make_stub_stage_class(name: str, calls: list[str], output: object = None) -> type:
    """`name`を`calls`へ記録するStub Stageクラスを生成する。

    `output`が指定されていればそれを返し、指定がなければ入力をそのまま返す
    （identity）。実Stage（DocumentAnalyzer等）はそれぞれ異なるコンストラクタ
    引数を取るため、`*args, **kwargs`を受け入れて無視することで、
    job_runner._build_document_stages()等からそのまま差し替え可能にする。
    """

    class _StubStage:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del context
            calls.append(name)
            return output if output is not None else input

    _StubStage.__name__ = f"Stub{name}"
    return _StubStage


def make_section_parser_stub_class(calls: list[str], section_count: int) -> type:
    """`section_count`件の`PersonnelSection`を持つ`SectionParseResult`を返すStub。"""

    class _StubSectionParser:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del context, input
            calls.append("section_parser")
            sections = tuple(make_section(i) for i in range(section_count))
            return SectionParseResult(sections=sections, candidates=(), confidence=_CONFIDENCE)

    return _StubSectionParser


def make_field_extractor_stub_class(
    calls: list[str],
    records_per_section: dict[int, int] | None = None,
    failing_section_indexes: frozenset[int] = frozenset(),
) -> type:
    """入力`PersonnelSection.section_index`に応じてrecord件数を変える、または失敗するStub。"""
    counts = records_per_section or {}

    class _StubFieldExtractor:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            calls.append("field_extractor")
            section = cast("PersonnelSection", input)
            if section.section_index in failing_section_indexes:
                raise PipelineException(
                    stage_name="field_extractor",
                    context=context,  # type: ignore[arg-type]
                    message=f"field_extractor failed for section {section.section_index}",
                )
            count = counts.get(section.section_index, 1)
            records = tuple(make_raw_record(i) for i in range(count))
            return FieldExtractionResult(records=records, candidates=(), confidence=_CONFIDENCE)

    return _StubFieldExtractor


def make_normalizer_stub_class(
    calls: list[str], failing_record_indexes: frozenset[int] = frozenset()
) -> type:
    """入力`RawRecord.record_index`に応じて失敗する、または`NormalizationResult`を返すStub。"""

    class _StubNormalizer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            calls.append("normalizer")
            raw = cast("RawRecord", input)
            if raw.record_index in failing_record_indexes:
                raise PipelineException(
                    stage_name="normalizer",
                    context=context,  # type: ignore[arg-type]
                    message=f"normalizer failed for record {raw.record_index}",
                )
            normalized = make_normalized_record(raw)
            return NormalizationResult(records=(normalized,), candidates=(), confidence=_CONFIDENCE)

    return _StubNormalizer


def make_validator_stub_class(
    calls: list[str], failing_record_indexes: frozenset[int] = frozenset()
) -> type:
    """入力`NormalizedRecord.raw_record_ref.record_index`に応じて失敗する、または`ValidationResult`を返すStub。"""

    class _StubValidator:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            calls.append("validator")
            normalized = cast("NormalizedRecord", input)
            record_index = normalized.raw_record_ref.record_index
            if record_index in failing_record_indexes:
                raise PipelineException(
                    stage_name="validator",
                    context=context,  # type: ignore[arg-type]
                    message=f"validator failed for record {record_index}",
                )
            return make_validation_result()

    return _StubValidator


def make_section(index: int = 0, *, pdf_id: int = 1) -> PersonnelSection:
    return PersonnelSection(
        document_ref=PdfId(pdf_id),
        layout_id="reiwa",
        section_index=index,
        section_label=None,
        page_range=(1, 1),
        section_text=f"section-{index}",
    )


def make_raw_record(index: int = 0) -> RawRecord:
    return RawRecord(
        section_ref=None,
        layout_id="reiwa",
        record_index=index,
        raw_fields={"column_1": f"value-{index}"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_normalized_record(raw: RawRecord) -> NormalizedRecord:
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={
            name: NormalizedValue(value=value, raw=value) for name, value in raw.raw_fields.items()
        },
        normalization_applied=(),
        normalized_at=raw.extracted_at,
    )


def make_validation_result(*, passed: bool = True) -> ValidationResult:
    evidence = ValidationEvidence(record_index=0, layout_id="reiwa", rules_evaluated=0)
    candidate = ValidationCandidate(
        record_index=0,
        score=1.0 if passed else 0.0,
        errors=(),
        warnings=(),
        evidence=evidence,
    )
    return ValidationResult(
        status="passed" if passed else "failed",
        candidates=(candidate,),
        confidence=_CONFIDENCE,
        validated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class StubKnowledgeService:
    def __init__(
        self,
        snapshot: KnowledgeSnapshot | None = None,
        rules: ValidationRuleSet | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self._snapshot = snapshot or KnowledgeSnapshot(
            items=(), snapshot_checksum="chk-1", as_of=_DEFAULT_AS_OF
        )
        self._rules = rules or ValidationRuleSet(rules=(), as_of=_DEFAULT_AS_OF)
        self._fail = fail
        self.load_snapshot_calls = 0
        self.load_validation_rules_calls = 0

    def load_snapshot(self, as_of: object = None) -> KnowledgeSnapshot:
        del as_of
        self.load_snapshot_calls += 1
        if self._fail:
            raise RuntimeError("KnowledgeService.load_snapshot failed")
        return self._snapshot

    def load_validation_rules(self, as_of: object = None) -> ValidationRuleSet:
        del as_of
        self.load_validation_rules_calls += 1
        return self._rules

    def get_item(self, category: str, item_key: str) -> KnowledgeItem | None:
        del category, item_key
        return None

    def reload(self) -> KnowledgeSnapshot:
        return self._snapshot


class StubLearningService:
    def __init__(self) -> None:
        self.recorded: list[LearningRecord] = []

    def record_error(self, entry: LearningRecord) -> LearningRecordId:
        self.recorded.append(entry)
        return LearningRecordId(len(self.recorded))

    def transition(self, record_id: object, new_status: object, **fields: object) -> LearningRecord:
        raise NotImplementedError

    def list_open(self) -> tuple[LearningRecord, ...]:
        return ()

    def summarize_by_error_category(self) -> dict[str, int]:
        return {}


class StubPDFRepository:
    def __init__(self, pending: tuple[PdfRecord, ...] = ()) -> None:
        self._pending = pending
        self._next_id = 1

    def add(self, pdf: PdfRecord) -> PdfId:
        pdf_id = PdfId(self._next_id)
        self._next_id += 1
        return pdf_id

    def get(self, pdf_id: PdfId) -> PdfRecord | None:
        del pdf_id
        return None

    def get_by_hash(self, content_hash: str) -> PdfRecord | None:
        del content_hash
        return None

    def update_status(self, pdf_id: PdfId, status: str) -> None:
        del pdf_id, status

    def list_by_status(self, status: str) -> tuple[PdfRecord, ...]:
        return tuple(p for p in self._pending if p.status == status)


@dataclass
class StubJobRepository:
    jobs: dict[int, Job] = field(default_factory=dict)
    updates: list[tuple[JobId, str, int, int]] = field(default_factory=list)
    add_should_fail: bool = False
    _next_id: int = 1

    def add(self, job: Job) -> JobId:
        if self.add_should_fail:
            raise RuntimeError("JobRepository.add failed")
        job_id = JobId(self._next_id)
        self._next_id += 1
        self.jobs[int(job_id)] = replace(job, id=job_id)
        return job_id

    def update_status(
        self, job_id: JobId, status: str, processed_count: int, failed_count: int
    ) -> None:
        self.updates.append((job_id, status, processed_count, failed_count))
        current = self.jobs[int(job_id)]
        self.jobs[int(job_id)] = replace(
            current,
            status=status,  # type: ignore[arg-type]
            processed_count=processed_count,
            failed_count=failed_count,
        )

    def get(self, job_id: JobId) -> Job | None:
        return self.jobs.get(int(job_id))

    def list_running(self) -> tuple[Job, ...]:
        return tuple(j for j in self.jobs.values() if j.status == "running")

    def record_parser_version(self, version: ParserVersion) -> ParserVersionId:
        del version
        return ParserVersionId(1)

    def get_parser_version(self, code_version: str) -> ParserVersion | None:
        del code_version
        return None

    def get_latest_parser_version(self) -> ParserVersion | None:
        return None


@dataclass
class StubCandidateRepository:
    """`CandidateRepository` Protocolを満たす、呼び出し記録付きの最小限のStub。

    `order_log`が渡された場合、Stage実行順序（`make_*_stub_class`のcallsリスト）
    と同じリストへ各メソッド呼び出しを記録し、Artifact Flowの順序を横断的に
    検証できるようにする。
    """

    order_log: list[str] | None = None
    add_section_calls: list[PersonnelSection] = field(default_factory=list)
    add_raw_calls: list[tuple[PersonnelSectionId, RawRecord]] = field(default_factory=list)
    attach_normalized_calls: list[tuple[CandidateId, NormalizedRecord]] = field(
        default_factory=list
    )
    update_validation_calls: list[tuple[CandidateId, ValidationResult]] = field(
        default_factory=list
    )
    _next_section_id: int = 1
    _next_candidate_id: int = 1

    def add_section(self, section: PersonnelSection) -> PersonnelSectionId:
        self.add_section_calls.append(section)
        if self.order_log is not None:
            self.order_log.append("add_section")
        section_id = PersonnelSectionId(self._next_section_id)
        self._next_section_id += 1
        return section_id

    def get_section(self, section_id: PersonnelSectionId) -> PersonnelSection | None:
        del section_id
        return None

    def add_raw(self, section_id: PersonnelSectionId, record: RawRecord) -> CandidateId:
        self.add_raw_calls.append((section_id, record))
        if self.order_log is not None:
            self.order_log.append("add_raw")
        candidate_id = CandidateId(self._next_candidate_id)
        self._next_candidate_id += 1
        return candidate_id

    def attach_normalized(self, candidate_id: CandidateId, normalized: NormalizedRecord) -> None:
        self.attach_normalized_calls.append((candidate_id, normalized))
        if self.order_log is not None:
            self.order_log.append("attach_normalized")

    def update_validation(self, candidate_id: CandidateId, result: ValidationResult) -> None:
        self.update_validation_calls.append((candidate_id, result))
        if self.order_log is not None:
            self.order_log.append("update_validation")

    def get(self, candidate_id: CandidateId) -> CandidateRecord | None:
        del candidate_id
        return None

    def list_by_section(self, section_id: PersonnelSectionId) -> tuple[CandidateRecord, ...]:
        del section_id
        return ()

    def list_pending_validation(self) -> tuple[CandidateRecord, ...]:
        return ()

    def list_failed_validation(self) -> tuple[CandidateRecord, ...]:
        return ()
