# opensearch-dummy-app

Standalone evaluation project to test whether OpenSearch is suitable as a log/trace
backend. Two dummy apps generate synthetic logs and traces, send them through
[Data Prepper](https://github.com/opensearch-project/data-prepper), which forwards them
into an existing 3-node OpenSearch VM cluster (private network, plain HTTP) reached via
an OpenShift load-balancer.

Not connected to Zabbix Portal or its GitOps repo, but reuses the same CI/CD pattern
as a template.

## Repo layout

- **`log-pipeline/`** — app repo: `dummy-app-http` (POSTs JSON log events to Data
  Prepper's `http` source) and `dummy-app-otel` (sends OTLP trace spans via gRPC to
  Data Prepper's `otel_trace_source`), plus the GitLab CI pipeline that builds/pushes
  both images.
- **`log-pipeline_GitOps/`** — GitOps repo: Helm charts for `dummy-app-http`,
  `dummy-app-otel`, and `data-prepper` (vendored into an umbrella `log-pipeline`
  chart), plus ArgoCD Application manifests for staging/production/dr (all deployed
  into the shared `devops` namespace).

See `log-pipeline_GitOps/CLAUDE.md` for full architecture, current cluster status, and
the critical "Data Prepper has no env-var substitution in pipelines.yaml" gotcha before
touching pipeline config.

## Status (as of 2026-07-28)

`dummy-app-http` confirmed working end-to-end — data lands in OpenSearch and is visible
via Discover in Dashboards. `dummy-app-otel` not yet confirmed.
