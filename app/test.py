import requests
import logging
from fluent import handler


h = handler.FluentHandler("test", host="127.0.0.1", port=24224, verbose=True)
f = handler.FluentRecordFormatter(
    {
        "host": "%(hostname)s",
        "where": "%(module)s.%(funcName)s",
        "type": "%(levelname)s",
        "stack_trace": "%(exc_text)s",
        "service": "test",
    }
)

h.setFormatter(f)
logger = logging.getLogger(__name__)
logger.addHandler(h)
logger.setLevel(logging.INFO)

logger.info("test")

requests.post(
    "http://127.0.0.1:9880/service.test",
    json={"test": "test"},
    headers={"Content-Type": "application/json"},
)
