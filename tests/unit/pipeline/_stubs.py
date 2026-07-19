"""テスト専用のStub Stage実装群。Parser実装（DocumentAnalyzer等）はここにも置かない。

各StubはPipelineStage[object, object]を満たす、テストの意図を1つだけ表現する
最小限のクラスである（本番コード src/mod_personnel_db/pipeline/ には含めない）。
"""

from dataclasses import dataclass, field

from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException


class IdentityStubStage:
    """入力をそのまま返す（=何もしない、正常系のためのStub）。"""

    def run(self, context: PipelineContext, input: object) -> object:
        return input


@dataclass
class RecordingStubStage:
    """呼び出されたことを記録しつつ、入力をそのまま返す（呼び出し順序検証用）。"""

    calls: list[str] = field(default_factory=list)
    label: str = "recording"

    def run(self, context: PipelineContext, input: object) -> object:
        self.calls.append(self.label)
        return input


class FailingStubStage:
    """常にPipelineExceptionを送出する（異常系: 捕捉されるべき失敗）。"""

    def __init__(self, message: str = "stub stage failed") -> None:
        self._message = message

    def run(self, context: PipelineContext, input: object) -> object:
        raise PipelineException(stage_name="failing_stub", context=context, message=self._message)


class CrashingStubStage:
    """PipelineExceptionではない未分類の例外を送出する（伝播すべき想定外バグ）。"""

    def run(self, context: PipelineContext, input: object) -> object:
        raise RuntimeError("unclassified crash")
