from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage

from ._stubs import IdentityStubStage


def test_stub_stage_satisfies_pipeline_stage_protocol(context: PipelineContext) -> None:
    stage: PipelineStage[object, object] = IdentityStubStage()

    assert stage.run(context, "value") == "value"


def test_pipeline_stage_public_api_is_run_only() -> None:
    public_names = [name for name in dir(PipelineStage) if not name.startswith("_")]

    assert public_names == ["run"]
