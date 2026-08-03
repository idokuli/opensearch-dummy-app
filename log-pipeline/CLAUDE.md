# log-pipeline

App repo for an OpenSearch evaluation stack — sends dummy logs/traces
through Data Prepper into an existing 3-node OpenSearch VM cluster (private
network, plain HTTP), to evaluate OpenSearch as a log/trace backend.
Standalone project — **not** connected to Zabbix_Portal's pipeline, but
reuses the same CI/CD pattern (`.gitlab-ci.yml` + `.gitlab/ci/`) as a
template.

Deployment manifests, the Data Prepper pipeline config, and full
architecture/status notes live in the companion GitOps repo:
**`../log-pipeline_GitOps/CLAUDE.md`** — read that file for current state,
the critical "Data Prepper has no env-var substitution" gotcha, and what's
confirmed working vs. not.

## What's here

- `apps/dummy-app-http` — POSTs JSON log events to Data Prepper's `http`
  source (`data-prepper:2021/log/ingest` by default).
- `apps/dummy-app-otel` — sends OTLP trace spans via gRPC to Data Prepper's
  `otel_trace_source` (`data-prepper:21890` by default).
- `.gitlab-ci.yml` + `.gitlab/ci/{common,detect,python,gitops}.yml` — builds
  and pushes both images, then pushes tag updates to the GitOps repo and
  bootstraps ArgoCD Applications there.

## Status (as of 2026-07-28)

`dummy-app-http` confirmed working end-to-end (data lands in OpenSearch,
visible via Discover in Dashboards). `dummy-app-otel` not yet confirmed.
