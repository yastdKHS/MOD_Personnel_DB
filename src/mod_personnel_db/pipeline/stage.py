"""全6段階（Document Analyzer〜Validator）が実装するジェネリックProtocol。

docs/api/pipeline.md#pipelinestage に対応する。本Task（Phase2 Task3）ではPipeline
Framework（骨格）のみを実装し、各段階の実装（DocumentAnalyzer等）は行わない
（実装はtests/unit/pipeline/のStub Stageに限定する）。
"""

from typing import Protocol, TypeVar

from mod_personnel_db.pipeline.context import PipelineContext

# docs/api/pipeline.mdのコード例は分散指定なしの TypeVar("TIn") / TypeVar("TOut") だが、
# mypy --strictは「Protocol中の不変TypeVarはPEP 544のcontravariant/covariant期待に反する」
# ([misc]エラー)として拒否するため、実装時にPhase2 Task3で分散を明示した
# （run()の型シグネチャ・意味論は変えていない。detailは完了報告のTODO参照）。
TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class PipelineStage(Protocol[TIn, TOut]):
    """公開APIはrun()のみ（docs/api/pipeline.md#設計原則-各stageはrunのみを公開する）。"""

    def run(self, context: PipelineContext, input: TIn) -> TOut: ...
