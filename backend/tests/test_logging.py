"""Provider keys must never reach the console."""
import logging

from backend.app.core.logger import RedactFilter, redact_url


def test_redact_url_masks_credentials():
    url = "https://pixabay.com/api/?key=56663950-abc&q=water&client_id=xyz&per_page=15"
    out = redact_url(url)
    assert "56663950-abc" not in out and "xyz" not in out
    assert "key=***" in out and "client_id=***" in out and "q=water" in out


def test_redact_filter_scrubs_log_records():
    record = logging.LogRecord("httpx", logging.INFO, __file__, 1, "GET %s", ("https://x.test/?api_key=SECRET1",), None)
    RedactFilter().filter(record)
    assert "SECRET1" not in record.getMessage()


def test_httpx_logger_is_quiet():
    import backend.app.core.logger  # noqa: F401
    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING


