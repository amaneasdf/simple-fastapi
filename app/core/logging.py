import logging
from fluent import handler

from .config import get_settings


class CustomLogger:
    """
    Custom logger class for structured logging with Fluentd.

    Attributes:
        service_name (str): The name of the service.
        instance_id (int): The instance ID of the service.
    """

    _settings = get_settings().logging

    def __init__(self, service_name: str, instance_id: str):
        """
        Initializes the logger with the given service name and instance ID.

        :param service_name: The name of the service.
        :type service_name: str
        :param instance_id: The instance ID of the service.
        :type instance_id: int
        """
        self.service_name = service_name
        self.instance_id = instance_id

        # Create an instance of LoggerProvider with a Resource object that includes
        # service name and instance ID, identifying the source of the logs.
        self.custom_format = {
            "host": "%(hostname)s",
            "where": "%(module)s.%(funcName)s",
            "type": "%(levelname)s",
            "stack_trace": "%(exc_text)s",
            "service": self.service_name,
            "instance_id": self.instance_id,
        }

        # Create a FluentHandler with the custom format.
        self.h = handler.FluentHandler(
            f"service.{self.service_name}",
            host=self._settings.agent_host,
            port=self._settings.agent_port,
        )

    def __del__(self):
        self.h.close()

    def get_logger(self):
        """
        Sets the logger and returns it
        """

        logger = logging.getLogger("uvicorn.error")
        logger.setLevel(self._settings.level)

        if self._settings.agent_enabled:
            # Add the FluentHandler to the logger
            formatter = handler.FluentRecordFormatter(self.custom_format)
            self.h.setFormatter(formatter)
            logger.addHandler(self.h)

        return logger


logger = CustomLogger(
    get_settings().service_name, get_settings().instance_id
).get_logger()
