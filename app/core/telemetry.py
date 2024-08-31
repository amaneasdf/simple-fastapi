from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    ConsoleSpanExporter,
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from .config import get_settings


_settings = get_settings()

provider = TracerProvider(resource=Resource({"service.name": "fastapi"}))


def get_tracer(name: str = "opentelemetry.instrumentation.fastapi") -> trace.Tracer:
    return provider.get_tracer(name)


def init_telemetry(app: FastAPI) -> None:
    if _settings.verbose_tracing:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    if _settings.telemetry_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=_settings.telemetry_endpoint,
            headers={_settings.telemetry_api_header: _settings.telemetry_api_key},
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)


def get_trace_id() -> str:
    return hex(trace.get_current_span().get_span_context().trace_id)[2:]


def shutdown_telemetry(app: FastAPI) -> None:
    provider.shutdown()

    if _settings.verbose_tracing:
        print("Tracing stopped")
