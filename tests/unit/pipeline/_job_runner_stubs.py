"""JobRunnerテスト専用のStub群。具象実装はsrc/には置かない（Phase3 Task10-1）。"""

from dataclasses import dataclass, field, replace
from datetime import date

from mod_personnel_db.models import (
    Job,
    JobId,
    KnowledgeItem,
    KnowledgeSnapshot,
    LearningRecord,
    LearningRecordId,
    ParserVersion,
    ParserVersionId,
    PdfId,
    PdfRecord,
    ValidationRuleSet,
)

_DEFAULT_AS_OF = date(2026, 1, 1)


def make_stub_stage_class(name: str, calls: list[str]) -> type:
    """`name`を`calls`へ記録し、入力をそのまま返すStub Stageクラスを生成する。

    実Stage（DocumentAnalyzer等）はそれぞれ異なるコンストラクタ引数を取るため、
    `*args, **kwargs`を受け入れて無視することで、job_runner._build_stages()から
    そのまま差し替え可能にする。
    """

    class _StubStage:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del context
            calls.append(name)
            return input

    _StubStage.__name__ = f"Stub{name}"
    return _StubStage


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
