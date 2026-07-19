"""パイプライン固有の例外。docs/api/pipeline.md#pipelineexception、
docs/api/python-contract.md#例外設計 に対応する。
"""

from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class PipelineException(MODPersonnelDBError):  # noqa: N818
    """パイプライン実行中に発生した例外の基底クラス。

    クラス名は`Error`接尾辞を持たないが、これはdocs/api/pipeline.md#pipelineexceptionと
    docs/api/python-contract.md#例外設計が明示的に定める正式名称であり、変更しない
    （ruffのN818「Exception名にはError接尾辞を付ける」規約と設計文書の名称が競合するため
    個別に抑制する）。

    特定Stageの失敗は、そのPDF・そのレコードの処理のみを失敗させ、他の処理には波及させない
    （ADR-0019）。PipelineRunnerはこの例外のみを捕捉し、それ以外の未分類の例外は
    想定外のバグとして再送出する（docs/api/python-contract.md#例外設計）。
    """

    def __init__(self, stage_name: str, context: PipelineContext, message: str) -> None:
        super().__init__(message)
        self._stage_name = stage_name
        self._context = context

    @property
    def stage_name(self) -> str:
        return self._stage_name

    @property
    def context(self) -> PipelineContext:
        return self._context


class PipelineFrameworkError(MODPersonnelDBError):
    """pipeline/内のdataclass不変条件違反・構築時（Builder/Factory）の誤用を表す。

    PipelineExceptionは「実行文脈（PipelineContext）が既に存在する状態でのStage失敗」を
    表すため、Stage実行前の構築段階の誤り（例: Stage未登録でのbuild()）や、
    PipelineMetrics/PipelineResult等pipeline/固有dataclassの`__post_init__`検証には
    使えない。本クラスはその隙間を埋める、pipeline/固有のもう一つのMODPersonnelDBError
    派生である（models/のModelValidationErrorはmodels.mdの13モデル専用のため転用しない）。
    """
