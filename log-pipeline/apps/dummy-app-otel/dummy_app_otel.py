"""
dummy_app_otel.py
Fake multi-service app that emits real OpenTelemetry traces. Simulates a
request flowing through three services: frontend -> orders-service ->
payment-service, so OpenSearch's Trace Analytics / Services map has
something meaningful to show.

Sends spans via OTLP gRPC straight to Data Prepper's otel_trace_source.
"""
import os
import random
import time

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

# PRIVATE NETWORK: no change needed here — this is the in-cluster Service name
# for Data Prepper, resolved via Kubernetes/OpenShift DNS, not an external host.
OTLP_ENDPOINT = os.environ.get("OTLP_ENDPOINT", "data-prepper:21890")
ROUTES = ["/checkout", "/cart", "/orders"]


def make_tracer(service_name: str):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider.get_tracer(service_name)


frontend_tracer = make_tracer("frontend")
orders_tracer = make_tracer("orders-service")
payment_tracer = make_tracer("payment-service")


def simulate_request():
    route = random.choice(ROUTES)
    with frontend_tracer.start_as_current_span(f"GET {route}") as root_span:
        root_span.set_attribute("http.method", "GET")
        root_span.set_attribute("http.route", route)
        time.sleep(random.uniform(0.01, 0.05))

        with orders_tracer.start_as_current_span("OrdersService.process") as orders_span:
            orders_span.set_attribute("component", "orders")
            time.sleep(random.uniform(0.02, 0.08))

            with payment_tracer.start_as_current_span("PaymentService.charge") as payment_span:
                payment_span.set_attribute("component", "payment")
                success = random.random() > 0.15
                time.sleep(random.uniform(0.02, 0.1))
                if success:
                    payment_span.set_status(Status(StatusCode.OK))
                else:
                    payment_span.set_status(Status(StatusCode.ERROR, "payment declined"))
                    payment_span.set_attribute("error", True)

        root_span.set_attribute("http.status_code", 200 if success else 500)


def main():
    print(f"dummy-app-otel sending traces to {OTLP_ENDPOINT}", flush=True)
    while True:
        simulate_request()
        print("sent trace", flush=True)
        time.sleep(random.uniform(1, 3))


if __name__ == "__main__":
    main()
