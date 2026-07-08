# SecurePrompt AI - Production Deployment Guide

This guide details the procedure for deploying the SecurePrompt AI containerized platform to a production server environment (e.g. Linux Ubuntu VM on AWS EC2, GCP Compute Engine, or Azure VM).

## 🏗️ Production Architecture Layout

The platform uses a layered security model:
1. **NGINX Reverse Proxy**: Outer layer. Binds to ports `80` and `443`. Implements SSL termination, request rate-limiting, security headers (CSP, HSTS), and routes API requests.
2. **FastAPI application container**: Internal network. Hosts the scan pipelines and handles web clients.
3. **MLflow container**: Exposes the model registry to backend containers.
4. **Prometheus & Grafana containers**: Collect metrics and render operational boards.
5. **MongoDB container**: Database service.

---

## 🚀 Step-by-Step Deployment

### Step 1: Clone the Repository to the Host
```bash
git clone https://github.com/your-org/secureprompt-ai.git /opt/secureprompt-ai
cd /opt/secureprompt-ai
```

### Step 2: Configure Production Environment Variables
Copy the production environment template and set real credentials:
```bash
cp .env.production .env
```
Ensure you generate strong random strings for secrets:
```bash
# Example generating secure keys
openssl rand -hex 32
```

### Step 3: Provision SSL Certificates
For secure HTTPS connections, place your TLS certificate and private key in the proxy directory:
- Certificate file: `nginx/certs/secureprompt.crt`
- Key file: `nginx/certs/secureprompt.key`

Uncomment the HTTPS block in [nginx.conf](file:///d:/SecurePrompt%20AI/nginx/nginx.conf) to activate SSL.

### Step 4: Launch the Production Container Cluster
Launch the compose system:
```bash
docker compose -f docker-compose.yml up -d --build
```

---

## 💾 Persistent Storage Volumes

To avoid data loss when containers restart, Docker maps local directories to the host:
- `mongo_data` (mapped to `/data/db` in Mongo container): Stores user credentials, audit history, threat logs, and alert items.
- `mlflow_data` (mapped to `/mlflow` in MLflow container): Stores registered model weight binary histories and mlflow sqlite database.
- `model_cache` (mapped to `/workspace/model` in Backend): Stores the active model binaries synced from MLflow registry.

---

## 🔒 Security Configuration Checklist

- [ ] **Firewall Ports**: Ensure only port `80` and `443` are exposed publicly in your cloud firewall (Security Group). Ports `27017` (MongoDB), `5000` (MLflow), `9090` (Prometheus), `3000` (Grafana), and `8000` (FastAPI backend) must only be accessible within the container network.
- [ ] **Rate Limiting**: NGINX limits requests to `10 requests/sec` with burst `20` per IP to prevent Denials of Service. Adjust these settings in `nginx.conf` if necessary.
- [ ] **Gzip compression**: Active for CSS, HTML, and JSON to minimize response payload latency.
