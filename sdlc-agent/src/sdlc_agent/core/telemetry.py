# =============================================================================
# SDLC Agent - OpenTelemetry Instrumentation
# =============================================================================
# Distributed tracing, metrics, and logging integration with OpenTelemetry.
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine

    from sdlc_agent.core.config import Settings


def setup_telemetry(settings: Settings) -> None:
    """
    Initialize OpenTelemetry tracing and metrics.

    Args:
        settings: Application settings
    """
    if not settings.observability.enabled:
        return

    # Create resource with service information
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.observability.service_name,
            ResourceAttributes.SERVICE_VERSION: "0.1.0",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.app.app_env.value,
        }
    )

    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(
        endpoint=str(settings.observability.exporter_otlp_endpoint),
        insecure=True,  # Set to False in production with TLS
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Setup metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=str(settings.observability.exporter_otlp_endpoint),
            insecure=True,
        ),
        export_interval_millis=60000,  # Export every 60 seconds
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)


def instrument_fastapi(app: FastAPI) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics",
    )


def instrument_sqlalchemy(engine: AsyncEngine) -> None:
    """
    Instrument SQLAlchemy with OpenTelemetry.

    Args:
        engine: SQLAlchemy async engine
    """
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        enable_commenter=True,
    )


def instrument_redis() -> None:
    """Instrument Redis client with OpenTelemetry."""
    RedisInstrumentor().instrument()


def instrument_httpx() -> None:
    """Instrument HTTPX client with OpenTelemetry."""
    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for creating spans.

    Args:
        name: Tracer name (typically module name)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Get a meter instance for creating metrics.

    Args:
        name: Meter name (typically module name)

    Returns:
        Meter instance
    """
    return metrics.get_meter(name)


# Create application-wide metrics
_meter = get_meter("sdlc_agent")

# Request metrics
request_counter = _meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1",
)

request_duration = _meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration in seconds",
    unit="s",
)

# Agent metrics
agent_execution_counter = _meter.create_counter(
    name="agent_executions_total",
    description="Total number of agent executions",
    unit="1",
)

agent_execution_duration = _meter.create_histogram(
    name="agent_execution_duration_seconds",
    description="Agent execution duration in seconds",
    unit="s",
)

llm_token_counter = _meter.create_counter(
    name="llm_tokens_total",
    description="Total LLM tokens used",
    unit="1",
)

llm_request_counter = _meter.create_counter(
    name="llm_requests_total",
    description="Total LLM API requests",
    unit="1",
)
