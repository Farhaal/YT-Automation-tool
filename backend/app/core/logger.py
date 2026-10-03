import logging
import re

from rich.logging import RichHandler

# Credentials some providers require in the query string (Pixabay uses ?key=...).
_SECRET_PARAM = re.compile(
    r"([?&](?:key|api_key|apikey|client_id|access_key|access_token|token)=)[^&\s\"']+",
    re.IGNORECASE,
)


def redact_url(text: str) -> str:
    """Mask credential values in a URL (or any text that contains one)."""
    if not text:
        return text
    return _SECRET_PARAM.sub(r"\1***", str(text))


class RedactFilter(logging.Filter):
    """Last line of defence: scrub credentials from every record before it is printed."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        cleaned = redact_url(message)
        if cleaned != message:
            record.msg = cleaned
            record.args = None
        return True


_handler = RichHandler(rich_tracebacks=True, markup=True)
_handler.addFilter(RedactFilter())

# Set up standard logging to use rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[_handler]
)

# httpx logs every request URL at INFO, which prints provider keys. Keep warnings only.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger("openreel")
