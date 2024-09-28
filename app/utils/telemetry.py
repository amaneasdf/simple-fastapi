from opentelemetry import trace
from app.core.telemetry import provider

current_span = trace.get_current_span()


class TracerDependency:
    def __init__(self, name: str = "opentelemetry.instrumentation.fastapi"):
        self.tracer = provider.get_tracer(name)

    def __call__(self):
        """
        Returns the tracer.
        Does not accept any arguments.
        """
        return self.tracer


def get_span_id() -> str:
    """
    Returns the span ID of the current span
    """
    return hex(current_span.get_span_context().span_id)[2:]


def get_trace_id() -> str:
    """
    Returns the trace ID of the current span
    """
    return hex(current_span.get_span_context().trace_id)[2:]
