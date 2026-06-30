#!/usr/bin/env bash
set -euo pipefail

ARGOCD_VERSION="${ARGOCD_VERSION:-stable}"

echo "Creating argocd namespace..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Argo CD (${ARGOCD_VERSION})..."
kubectl apply -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

echo "Waiting for Argo CD server..."
kubectl -n argocd rollout status deployment/argocd-server --timeout=300s

echo "Applying Lyubava AppProject and Application..."
kubectl apply -f k8s/argocd/appproject.yaml
kubectl apply -f k8s/argocd/application.yaml

cat <<'EOF'

Argo CD is installed.

Next steps:
1. Create GHCR pull secret in namespace lyubava (see docs/argocd.md).
2. Copy k8s/minikube/.env.example to k8s/minikube/.env and fill values.
3. Open the Argo CD UI and sync the "lyubava" application.

Port-forward UI:
  kubectl -n argocd port-forward svc/argocd-server 8080:443

Initial admin password:
  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
EOF
