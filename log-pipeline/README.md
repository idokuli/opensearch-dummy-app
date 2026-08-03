# log-pipeline

Standalone evaluation project — **not** connected to Zabbix Portal or its
GitOps repo. Reuses the same CI/CD pipeline pattern, deployed independently.

Sends dummy logs and traces through [Data Prepper](https://github.com/opensearch-project/data-prepper)
into an existing OpenSearch cluster (3 VMs, private network, plain HTTP, no
security plugin) reached via an OpenShift load-balancer deployment, to
evaluate whether OpenSearch is suitable as a log/trace backend.

## Components

| App | Sends | To |
|---|---|---|
| `apps/dummy-app-http` | JSON log events via HTTP POST | Data Prepper `http` source (`:2021/log/ingest`) |
| `apps/dummy-app-otel` | OTLP traces via gRPC | Data Prepper `otel_trace_source` (`:21890`) |

Data Prepper itself, the OpenSearch sink config, and deployment manifests
live in the companion **log-pipeline_GitOps** repo (`helm-charts/data-prepper`),
since Data Prepper uses the upstream `opensearchproject/data-prepper` image
(mirrored to your Artifactory) rather than a custom build.

## GitOps repo

`../log-pipeline_GitOps` — umbrella chart `helm-charts/log-pipeline`,
deployed via ArgoCD into namespace `devops` for all three environments
(staging/production/dr share that namespace; each environment gets its own
release-name-prefixed resources, so nothing collides).

## Status (as of 2026-07-28)

`dummy-app-http` confirmed working end-to-end — data lands in OpenSearch
and is visible via **Discover** in Dashboards. `dummy-app-otel` not yet
confirmed.

See `../log-pipeline_GitOps/CLAUDE.md` for full architecture/status notes
and the critical "Data Prepper has no env-var substitution" gotcha before
touching `pipelines.yaml` or `data-prepper-config.yaml`.

## Private network checklist

See the `PRIVATE NETWORK` comments in each `Dockerfile` and `.gitlab-ci.yml`
— every placeholder (`<your-...>`) must be filled in before this pipeline
will run.
