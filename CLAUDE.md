# opensearch-dummy-app

Standalone evaluation project — **not** connected to Zabbix Portal or its GitOps
repo, but reuses the same CI/CD pattern as a template. Purpose: send dummy logs and
traces through [Data Prepper](https://github.com/opensearch-project/data-prepper)
into an existing OpenSearch cluster (3 VMs, private network, plain HTTP) reached via
an OpenShift load-balancer, to evaluate whether OpenSearch is suitable as a log/trace
backend.

## Repo layout (two git repos live side by side here)

- **`log-pipeline/`** — app repo. `apps/dummy-app-http` POSTs JSON log events to
  Data Prepper's `http` source (`:2021/log/ingest`). `apps/dummy-app-otel` sends
  OTLP trace spans via gRPC to Data Prepper's `otel_trace_source` (`:21890`),
  simulating a frontend -> orders-service -> payment-service call chain. Also has
  the GitLab CI pipeline (`.gitlab-ci.yml` + `.gitlab/ci/`) that builds/pushes both
  images and bootstraps the GitOps repo.
- **`log-pipeline_GitOps/`** — GitOps repo. Helm charts for `dummy-app-http`,
  `dummy-app-otel`, and `data-prepper` (Deployment + Service + ConfigMap for
  `pipelines.yaml`/`data-prepper-config.yaml`), vendored into an umbrella
  `log-pipeline` chart. ArgoCD Application manifests deploy staging/production/dr
  all into the shared `devops` namespace (deliberate — one eval project backed by
  one real OpenSearch cluster).

**Read the nested `CLAUDE.md` in whichever of those two directories you're working
in** — each has fuller, up-to-date architecture/status notes than this file.
`log-pipeline_GitOps/CLAUDE.md` in particular has the critical gotchas below.

## Critical gotchas (do not relearn these the hard way)

- **Data Prepper has NO env-var substitution in `pipelines.yaml`.** Confirmed with
  an OpenSearch maintainer — `${VAR}` / `${env:VAR}` do not resolve; only AWS
  Secrets Manager refs are supported, which don't apply here. The working setup
  writes real OpenSearch username/password **directly in plaintext** into the
  `opensearch` sink blocks of `pipelines.yaml`. Do not reintroduce env-var
  placeholders expecting them to resolve at runtime.
- **When editing any standalone Helm chart under `log-pipeline_GitOps/helm-charts/<name>/`,
  re-copy it into `helm-charts/log-pipeline/charts/<name>/`** — ArgoCD/Helm renders
  from the vendored copy only.
- OpenSearch's security plugin is **enabled** (plain HTTP, but auth is still
  enforced) — contrary to the original "unsecured" assumption.
- Every `PRIVATE NETWORK` comment (Dockerfiles, `.gitlab-ci.yml`) marks a
  placeholder that must be filled in with real values before the pipeline runs.

## Status (as of 2026-07-28)

`dummy-app-http` confirmed working end-to-end — data lands in OpenSearch and is
visible via **Discover** in OpenSearch Dashboards (not another "logs" view — an
index pattern must exist first). `dummy-app-otel` not yet confirmed end-to-end.
