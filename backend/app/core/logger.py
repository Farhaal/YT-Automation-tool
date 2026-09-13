import logging
from rich.logging import RichHandler

# Set up standard logging to use rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger("openreel")
