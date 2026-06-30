# Minikube deployment

This repository includes a local Kubernetes stack for minikube:

- FastAPI backend with the local emotion model baked into `lyubava-api:latest`.
- React frontend served by nginx as `lyubava-frontend:latest`.
- nginx proxy from `/api/*` to the in-cluster backend service.
- MLflow server with Postgres metadata storage and MinIO artifact storage.
- Prometheus scraping `/metrics` from the API.
- Grafana with the bundled Lyubava dashboard provisioned at startup.

## Prerequisites

- Docker
- minikube
- kubectl
- the local model files in `models/emotion_classifier`

The API image expects the model directory to exist before the image is built. If it is missing, restore it with DVC first.

## Start minikube

```powershell
minikube start --cpus 4 --memory 8192 --disk-size 30g
```

## Build images inside minikube

PowerShell:

```powershell
minikube image build -t lyubava-api:latest -f Dockerfile .
minikube image build -t lyubava-mlflow:latest -f Dockerfile.mlflow .
minikube image build -t lyubava-frontend:latest frontend
```

By default the frontend image is built with `VITE_CHAT_MOCK=true`, so the chat screen opens even without an OpenRouter key. To route chat messages to the backend LLM endpoint, rebuild it with:

```powershell
minikube image build -t lyubava-frontend:latest --build-arg VITE_CHAT_MOCK=false frontend
```

Then set `OPENROUTER_API_KEY` in the local `k8s/minikube/.env` file before applying the manifests.

## Deploy

Create a local Kubernetes env file first. This file is ignored by git and is used by kustomize to generate the `lyubava-secrets` Kubernetes Secret:

```powershell
Copy-Item k8s/minikube/.env.example k8s/minikube/.env
```

Edit `k8s/minikube/.env` and set local values for the backend, Postgres, MinIO, AWS-compatible MinIO credentials, MLflow, Grafana admin credentials, and optionally `OPENROUTER_API_KEY`.

```powershell
kubectl apply -k k8s/minikube
kubectl -n lyubava rollout status deployment/api
kubectl -n lyubava rollout status deployment/frontend
kubectl -n lyubava rollout status deployment/mlflow
kubectl -n lyubava rollout status deployment/prometheus
kubectl -n lyubava rollout status deployment/grafana
```

Check everything:

```powershell
kubectl -n lyubava get pods
kubectl -n lyubava get svc
```

## Open services

Use minikube helpers:

```powershell
minikube service -n lyubava frontend
minikube service -n lyubava api
minikube service -n lyubava mlflow
minikube service -n lyubava grafana
minikube service -n lyubava minio
```

Fixed NodePorts are also configured:

- Frontend: `http://$(minikube ip):30000`
- API: `http://$(minikube ip):30080`
- Prometheus: `http://$(minikube ip):30090`
- Grafana: `http://$(minikube ip):30300` (credentials from `k8s/minikube/.env`)
- MLflow: `http://$(minikube ip):30500`
- MinIO API: `http://$(minikube ip):30900`
- MinIO console: `http://$(minikube ip):30901` (credentials from `k8s/minikube/.env`)

On Windows, `minikube service -n lyubava frontend` is usually the most reliable way to open the frontend because the driver may not expose NodePorts directly on the host.

## DVC with MinIO

The default DVC remote (`origin`) is configured to use MinIO (`s3://dvc`).

The minikube manifests create the `dvc` bucket automatically via the `minio-create-buckets` job.

Set local credentials in `config.local` (never committed):

```powershell
dvc remote modify --local origin access_key_id minioadmin
dvc remote modify --local origin secret_access_key minioadmin123
```

Choose the endpoint depending on how you access MinIO from the host:

1. **Via NodePort**

   ```powershell
   $MINIKUBE_IP = minikube ip
   dvc remote modify --local origin endpointurl "http://$MINIKUBE_IP`:30900"
   ```

2. **Via port-forward**

   ```powershell
   kubectl -n lyubava port-forward svc/minio 9000:9000
   dvc remote modify --local origin endpointurl http://localhost:9000
   ```

Then sync artifacts:

```powershell
dvc pull models.dvc
dvc push models.dvc
```

## Useful commands

```powershell
kubectl -n lyubava logs deployment/api
kubectl -n lyubava logs deployment/frontend
kubectl -n lyubava describe pod -l app.kubernetes.io/name=api
kubectl -n lyubava port-forward svc/frontend 8080:80
kubectl -n lyubava port-forward svc/api 8000:8000
```

## Remove the stack

```powershell
kubectl delete -k k8s/minikube
```

Persistent volumes created by Postgres and MinIO may remain after deleting the stack. Remove them manually only when you no longer need local MLflow data.
