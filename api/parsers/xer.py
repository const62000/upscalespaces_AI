try:
    from xer_reader import XerReader  # provided by the external 'xer-reader' package
    _XER_READER_AVAILABLE = True
except ImportError:
    _XER_READER_AVAILABLE = False

    class XerReader:  # minimal stub to avoid import-time failures
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "xer_reader package not installed. Install 'xer-reader' to enable XER parsing."
            )


def xer_parser(file_path: str):
    """Create and return an XerReader document for the given file path.

    Raises a clear error if the xer_reader dependency is unavailable.
    """
    if not _XER_READER_AVAILABLE:
        raise RuntimeError(
            "xer_reader package not installed. Install 'xer-reader' to use XER parsing."
        )

    xer_doc = XerReader(file_path)
    return xer_doc



