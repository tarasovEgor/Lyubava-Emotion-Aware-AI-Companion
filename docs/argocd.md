# Argo CD + GitOps deployment

This guide explains how Lyubava is deployed with Argo CD instead of manual `kubectl apply`.

## Architecture

```text
GitHub Actions (CD)  ->  GHCR images (api / frontend / mlflow)
        |
        v
git: k8s/overlays/argocd  ->  Argo CD sync  ->  Kubernetes (namespace lyubava)
```

- **CI** still runs tests and docker smoke checks.
- **CD** builds and pushes container images to GHCR.
- **Argo CD** watches `k8s/overlays/argocd` in this repository and applies the stack to the cluster.

Manual `kubectl apply -k k8s/minikube` remains available for local image builds. For GitOps use the Argo CD overlay.

## Prerequisites

- Kubernetes cluster (minikube is fine)
- `kubectl`
- Images published by CD to GHCR
- `k8s/minikube/.env` filled from `.env.example` (used by kustomize secret generation)

## 1. Install Argo CD

```bash
chmod +x scripts/argocd_bootstrap.sh
./scripts/argocd_bootstrap.sh
```

## 2. Create GHCR pull secret

If GHCR packages are private, create a pull secret in `lyubava`:

```bash
kubectl create namespace lyubava --dry-run=client -o yaml | kubectl apply -f -

kubectl -n lyubava create secret docker-registry ghcr-credentials \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-pat-with-read:packages> \
  --dry-run=client -o yaml | kubectl apply -f -
```

For public GHCR packages you may still need this secret depending on cluster settings.

## 3. Configure application secrets

```bash
cp k8s/minikube/.env.example k8s/minikube/.env
# edit k8s/minikube/.env
```

Argo CD renders secrets from this file through the base kustomize overlay.

## 4. Sync the application

Open the UI:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Visit https://localhost:8080 and sync the `lyubava` application.

Or sync from CLI after logging in:

```bash
argocd app sync lyubava
```

## Image tags

CD publishes:

| Service | Tags |
|---------|------|
| API | `api-latest`, `api-<sha>` |
| Frontend | `frontend-latest`, `frontend-<sha>` |
| MLflow | `mlflow-latest`, `mlflow-<sha>` |

`k8s/overlays/argocd/kustomization.yaml` points deployments to the `*-latest` tags.

## Local minikube without Argo CD

Build images locally and deploy the base overlay:

```bash
minikube image build -t lyubava-api:latest -f Dockerfile .
minikube image build -t lyubava-frontend:latest frontend
minikube image build -t lyubava-mlflow:latest -f Dockerfile.mlflow .
kubectl apply -k k8s/minikube
```

See also [minikube.md](./minikube.md).

## Files

| Path | Purpose |
|------|---------|
| `k8s/argocd/appproject.yaml` | Argo CD project |
| `k8s/argocd/application.yaml` | Argo CD Application (GitOps entry point) |
| `k8s/overlays/argocd/` | GHCR image tags + pull policy patch |
| `scripts/argocd_bootstrap.sh` | Install Argo CD and register the app |
