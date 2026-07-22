"""`fetch/`例外階層の検証（Phase7 Task16-3）。"""

from mod_personnel_db.fetch import (
    FetchContentTypeError,
    FetchError,
    FetchNetworkError,
    FetchStatusError,
    FetchTimeoutError,
    FetchValidationError,
)
from mod_personnel_db.utils.exceptions import MODPersonnelDBError


def test_fetch_error_is_mod_personnel_db_error() -> None:
    assert issubclass(FetchError, MODPersonnelDBError)


def test_all_specific_errors_are_fetch_errors() -> None:
    for exc_type in (
        FetchValidationError,
        FetchTimeoutError,
        FetchNetworkError,
        FetchStatusError,
        FetchContentTypeError,
    ):
        assert issubclass(exc_type, FetchError)


def test_status_error_carries_status_code() -> None:
    error = FetchStatusError("boom", status_code=404)

    assert error.status_code == 404


def test_content_type_error_carries_content_type() -> None:
    error = FetchContentTypeError("boom", content_type="text/html")

    assert error.content_type == "text/html"
