"""`ftp/`例外階層の検証（Phase7 Task16-1）。"""

from mod_personnel_db.ftp import FTPClientError, FTPConnectionError, FTPTransferError
from mod_personnel_db.utils.exceptions import MODPersonnelDBError


def test_ftp_client_error_is_mod_personnel_db_error() -> None:
    assert issubclass(FTPClientError, MODPersonnelDBError)


def test_ftp_connection_error_is_ftp_client_error() -> None:
    assert issubclass(FTPConnectionError, FTPClientError)


def test_ftp_transfer_error_is_ftp_client_error() -> None:
    assert issubclass(FTPTransferError, FTPClientError)


def test_ftp_connection_error_and_transfer_error_are_distinct() -> None:
    assert not issubclass(FTPConnectionError, FTPTransferError)
    assert not issubclass(FTPTransferError, FTPConnectionError)
