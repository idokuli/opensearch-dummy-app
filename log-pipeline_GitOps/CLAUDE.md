# log-pipeline_GitOps

GitOps repo for the `log-pipeline` OpenSearch evaluation stack. Standalone
project — **not** connected to Zabbix_Portal or its GitOps repo, but reuses
the same CI/CD/Helm/ArgoCD pattern as a template. Companion app repo:
`../log-pipeline` (dummy-app-http, dummy-app-otel).

## Architecture

```
dummy-app-http  --HTTP POST-->  data-prepper (http source, :2021)
dummy-app-otel  --OTLP gRPC-->  data-prepper (otel_trace_source, :21890)
                                       |
                                       v  opensearch sink, plain HTTP
                              load-balancer (existing OpenShift Deployment)
                                       |
                                       v
                        3x OpenSearch VMs (private network, 3.7.0)
```

OpenSearch and OpenSearch Dashboards run on 3 VMs outside OpenShift — not
deployed by this repo. The load-balancer is a pre-existing OpenShift
Deployment in front of those VMs — also not managed by this repo.

## What's in this repo

- `helm-charts/dummy-app-http`, `helm-charts/dummy-app-otel` — simple
  Deployment-only charts (no Service, they don't receive traffic).
- `helm-charts/data-prepper` — Deployment + Service (ports 2021 http-source,
  21890 otel-grpc, 4900 health) + ConfigMap for `pipelines.yaml` /
  `data-prepper-config.yaml`.
- `helm-charts/log-pipeline` — umbrella chart vendoring the three above into
  `charts/`. **When editing any standalone chart under `helm-charts/<name>/`,
  you MUST re-copy it into `helm-charts/log-pipeline/charts/<name>/`** —
  ArgoCD/Helm renders from the vendored copy, not the standalone one. This
  bit us once already (edited the standalone chart, `helm template` kept
  showing old behavior until we re-vendored). Quick command:
  ```bash
  rm -rf helm-charts/log-pipeline/charts/<name>
  cp -r helm-charts/<name> helm-charts/log-pipeline/charts/
  ```
- `argocd/application-{staging,production,dr}.yaml` — all three deploy into
  the **same namespace, `devops`** (deliberate — this is one eval project
  backed by one real OpenSearch cluster, not three isolated environments).
  Each environment gets a unique release name (`log-pipeline-staging` etc.),
  so Helm's default resource naming (`<release>-<chart>`) keeps them from
  colliding even sharing one namespace.

## Critical gotcha: Data Prepper has NO env-var substitution in pipelines.yaml

Confirmed directly with an OpenSearch maintainer (forum thread + GitHub
issue #2461): Data Prepper does **not** support `${VAR}`, `${env:VAR}`, or
any other environment-variable substitution syntax in `pipelines.yaml`. The
only supported secret-reference mechanism is AWS Secrets Manager
(`${{aws_secrets:...}}`), which doesn't apply to an on-prem OpenSearch
cluster like this one.

**Do not reintroduce `${OPENSEARCH_USERNAME}`/`${OPENSEARCH_PASSWORD}` (or
similar) placeholders in pipelines.yaml expecting them to resolve at
runtime — they will be sent to OpenSearch as literal strings and auth will
fail with `Unauthorized access`.** This was tried, debugged at length (see
below), and confirmed broken.

The only thing that actually works with this Data Prepper version: write
the real username/password **directly, in plaintext**, into
`pipelines.yaml`'s `opensearch` sink blocks (all three: `log-pipeline`,
`raw-trace-pipeline`, `service-map-pipeline`).

## Current live cluster state (as of 2026-07-28)

- OpenSearch's security plugin turned out to be **enabled** (contrary to the
  original "unsecure version" assumption) — plain HTTP but still enforces
  auth. Confirmed via `Unauthorized access` in data-prepper logs, and the
  `security_authentication` cookie in the WARN spam is the tell.
- `oc create configmap opensearch-configmap` and
  `oc create secret generic opensearch-secrets` were created **manually** in
  namespace `devops` (not via `oc create configmap/secret --from-file` off
  a chart-rendered file initially — hand-edited in the OpenShift console).
  `values-{staging,production,dr}.yaml` all set:
  ```yaml
  data-prepper:
    existingConfigMap: "opensearch-configmap"
    existingSecret: "opensearch-secrets"
    openSearch:
      auth:
        enabled: true
  ```
- **Confirmed working end-to-end**: dummy-app-http → data-prepper →
  OpenSearch, with real plaintext credentials manually entered into
  `opensearch-configmap`'s `pipelines.yaml` content. Data is visible in
  OpenSearch Dashboards' **Discover** tab (not some other "logs" view — that
  tripped us up once; Discover is where ingested documents actually show up,
  and requires an index pattern to be created first).
- `dummy-app-otel` (traces) — not yet confirmed working end-to-end, only the
  log pipeline has been verified.

## Known inconsistency to resolve

The chart's `data-prepper` still has vestigial `OPENSEARCH_USERNAME`/
`OPENSEARCH_PASSWORD` Secret + env var wiring (`templates/secret.yaml`,
`env:` block in `templates/deployment.yaml`, `existingSecret` in
`values.yaml`) left over from the broken `${VAR}`-substitution attempt.
Since the real working setup uses plaintext credentials baked directly into
`pipelines.yaml` instead, this env var/Secret machinery is currently
**unused dead weight** — `existingSecret` in the live values files points at
a Secret whose `username`/`password` keys nothing actually reads anymore.
Not yet cleaned up — pending decision on whether to delete it or keep it for
some other purpose.

## Reference files

`helm-charts/data-prepper/files/pipelines.yaml` and
`data-prepper-config.yaml` are **not** consumed by the Helm templates —
they're plain reference copies for when using the `existingConfigMap` path
(so there's something to `oc create configmap --from-file=` against, and to
diff/copy from without retyping). Keep them in sync with whatever the actual
manually-managed ConfigMap in the cluster contains.
