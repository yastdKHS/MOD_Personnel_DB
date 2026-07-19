import pytest

from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException, PipelineFrameworkError
from mod_personnel_db.utils.exceptions import MODPersonnelDBError


def test_pipeline_exception_exposes_stage_name_and_context(context: PipelineContext) -> None:
    exc = PipelineException(stage_name="normalizer", context=context, message="boom")

    assert exc.stage_name == "normalizer"
    assert exc.context is context
    assert str(exc) == "boom"


def test_pipeline_exception_is_mod_personnel_db_error(context: PipelineContext) -> None:
    exc = PipelineException(stage_name="normalizer", context=context, message="boom")

    assert isinstance(exc, MODPersonnelDBError)


def test_pipeline_exception_is_raisable(context: PipelineContext) -> None:
    with pytest.raises(PipelineException) as excinfo:
        raise PipelineException(stage_name="validator", context=context, message="invalid")

    assert excinfo.value.stage_name == "validator"


def test_pipeline_framework_error_is_mod_personnel_db_error() -> None:
    assert issubclass(PipelineFrameworkError, MODPersonnelDBError)


def test_pipeline_framework_error_is_not_pipeline_exception() -> None:
    assert not issubclass(PipelineFrameworkError, PipelineException)
