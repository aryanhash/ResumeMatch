# 🚀 Kestra Self-Hosted Deployment Guide

## Overview

This guide covers deploying Kestra using **Option B: Self-hosted with Docker**. Kestra will orchestrate your multi-agent pipeline for resume optimization.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM available
- Port 8080 available (or change in config)
- Backend code accessible (for task execution)

---

## 🐳 Option 1: Local Development (Docker Compose)

### Quick Start

```bash
# From project root
docker-compose up kestra
```

This will:
- Start Kestra on `http://localhost:8080`
- Mount your `kestra/` directory for workflows
- Persist data in Docker volume

### Access Kestra UI

1. Open browser: `http://localhost:8080`
2. Default credentials:
   - **Username**: `admin`
   - **Password**: `password` (change on first login!)

### Upload Workflow

**Method 1: Via UI**
1. Go to Kestra UI → **Flows** → **Create**
2. Copy content from `kestra/autoapplyai_pipeline.yaml`
3. Paste and save

**Method 2: Via API**
```bash
# Get auth token first
curl -X POST http://localhost:8080/api/v1/auths/basic/default \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Upload workflow
curl -X POST http://localhost:8080/api/v1/flows/autoapplyai/autoapplyai_pipeline \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @kestra/autoapplyai_pipeline.yaml
```

**Method 3: File Mount (Automatic)**
- If you mount `./kestra:/app/flows` in docker-compose
- Kestra will auto-discover workflows in `/app/flows/`

---

## ☁️ Option 2: Production Deployment

### Standalone Docker Container

```bash
# Run Kestra standalone
docker run -d \
  --name kestra \
  -p 8080:8080 \
  -v $(pwd)/kestra:/app/flows \
  -v kestra-data:/app/.kestra \
  -e KESTRA_CONFIGURATION_FILE=/app/flows/kestra-config.yml \
  kestra/kestra:latest \
  server standalone
```

### With Custom Configuration

Create `kestra/kestra-production.yml`:

```yaml
kestra:
  server:
    port: 8080
    base-path: /
    
  repository:
    type: local
    
  queue:
    type: memory
    
  storage:
    type: local
    local:
      basePath: /app/.kestra/storage
      
  encryption:
    enabled: true
    secret-key: ${KESTRA_ENCRYPTION_KEY}  # Set in env
    
  plugins:
    defaults:
      python:
        python-path: python3
        
  variables:
    env-vars-prefix: "KESTRA_"

logging:
  level:
    io.kestra: INFO
```

Run with custom config:
```bash
docker run -d \
  --name kestra \
  -p 8080:8080 \
  -v $(pwd)/kestra:/app/flows \
  -v kestra-data:/app/.kestra \
  -e KESTRA_CONFIGURATION_FILE=/app/flows/kestra-production.yml \
  -e KESTRA_ENCRYPTION_KEY=your-secret-key-here \
  kestra/kestra:latest \
  server standalone
```

---

## 🌐 Option 3: Cloud Deployment (Self-Hosted)

### Railway

1. **Create `kestra/Dockerfile`**:
```dockerfile
FROM kestra/kestra:latest

# Copy configuration
COPY kestra-config.yml /app/flows/kestra-config.yml
COPY autoapplyai_pipeline.yaml /app/flows/autoapplyai_pipeline.yaml

# Expose port
EXPOSE 8080

# Run Kestra
CMD ["server", "standalone"]
```

2. **Deploy on Railway**:
   - New Project → Deploy from GitHub
   - Root Directory: `kestra`
   - Port: `8080`
   - Environment Variables:
     ```
     KESTRA_CONFIGURATION_FILE=/app/flows/kestra-config.yml
     KESTRA_ENCRYPTION_KEY=your-secret-key
     ```

### Render

1. **New Web Service** → Docker
2. **Docker Image**: `kestra/kestra:latest`
3. **Docker Command**: `server standalone`
4. **Port**: `8080`
5. **Volumes**: Mount `kestra/` directory
6. **Environment**:
   ```
   KESTRA_CONFIGURATION_FILE=/app/flows/kestra-config.yml
   ```

### Fly.io

1. **Create `kestra/fly.toml`**:
```toml
app = "your-kestra-app"
primary_region = "iad"

[build]
  image = "kestra/kestra:latest"

[env]
  KESTRA_CONFIGURATION_FILE = "/app/flows/kestra-config.yml"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

2. **Deploy**:
```bash
cd kestra
fly launch
fly secrets set KESTRA_ENCRYPTION_KEY=your-secret-key
fly deploy
```

### DigitalOcean App Platform

1. **New App** → Docker
2. **Dockerfile Path**: `kestra/Dockerfile`
3. **Port**: `8080`
4. **Environment Variables**: Set KESTRA config vars
5. **Deploy**

---

## 🔗 Connecting Backend to Kestra

### Option A: Webhook Trigger (Recommended)

Your workflow already has a webhook trigger configured:

```yaml
triggers:
  - id: api_trigger
    type: io.kestra.plugin.core.trigger.Webhook
    key: autoapply_webhook
```

**Backend Integration** (add to `backend/main.py`):

```python
import httpx

KESTRA_URL = os.getenv("KESTRA_URL", "http://localhost:8080")
KESTRA_USERNAME = os.getenv("KESTRA_USERNAME", "admin")
KESTRA_PASSWORD = os.getenv("KESTRA_PASSWORD", "password")

async def trigger_kestra_workflow(resume_text: str, job_description: str):
    """Trigger Kestra workflow via webhook"""
    
    # Get auth token
    async with httpx.AsyncClient() as client:
        auth_response = await client.post(
            f"{KESTRA_URL}/api/v1/auths/basic/default",
            json={
                "username": KESTRA_USERNAME,
                "password": KESTRA_PASSWORD
            }
        )
        token = auth_response.json()["token"]
        
        # Trigger workflow
        webhook_response = await client.post(
            f"{KESTRA_URL}/api/v1/executions/webhook/autoapplyai/autoapplyai_pipeline/autoapply_webhook",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "resume_text": resume_text,
                "job_description": job_description
            }
        )
        
        execution_id = webhook_response.json()["id"]
        return execution_id

async def get_kestra_execution_status(execution_id: str):
    """Get execution status from Kestra"""
    
    async with httpx.AsyncClient() as client:
        auth_response = await client.post(
            f"{KESTRA_URL}/api/v1/auths/basic/default",
            json={
                "username": KESTRA_USERNAME,
                "password": KESTRA_PASSWORD
            }
        )
        token = auth_response.json()["token"]
        
        status_response = await client.get(
            f"{KESTRA_URL}/api/v1/executions/{execution_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return status_response.json()
```

### Option B: Direct API Call

```python
async def trigger_kestra_execution(resume_text: str, job_description: str):
    """Trigger Kestra execution via API"""
    
    async with httpx.AsyncClient() as client:
        auth_response = await client.post(
            f"{KESTRA_URL}/api/v1/auths/basic/default",
            json={
                "username": KESTRA_USERNAME,
                "password": KESTRA_PASSWORD
            }
        )
        token = auth_response.json()["token"]
        
        # Create execution
        execution_response = await client.post(
            f"{KESTRA_URL}/api/v1/executions/autoapplyai/autoapplyai_pipeline",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inputs": {
                    "resume_text": resume_text,
                    "job_description": job_description
                }
            }
        )
        
        return execution_response.json()["id"]
```

---

## 🔧 Configuration

### Environment Variables

Add to your `.env` or platform config:

```env
# Kestra Connection
KESTRA_URL=http://localhost:8080
KESTRA_USERNAME=admin
KESTRA_PASSWORD=your-secure-password

# For Kestra tasks (if needed)
KESTRA_TOGETHER_API_KEY=your_together_key
KESTRA_BACKEND_PATH=/app/backend
```

### Update Backend CORS (if needed)

If Kestra and backend are on different domains:

```python
# backend/main.py
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080"
).split(",")
```

---

## 📊 Monitoring & Logs

### View Logs

**Docker Compose**:
```bash
docker-compose logs -f kestra
```

**Docker**:
```bash
docker logs -f kestra
```

### Access Kestra UI

- **URL**: `http://your-kestra-url:8080`
- **Executions**: View all workflow runs
- **Logs**: Real-time task logs
- **Metrics**: Performance monitoring

### Health Check

```bash
curl http://localhost:8080/api/v1/configs
```

---

## 🔒 Security Best Practices

### 1. Change Default Password

```bash
# Via UI: Settings → Users → Change Password
# Or via API (see Kestra docs)
```

### 2. Enable Encryption

Update `kestra-config.yml`:
```yaml
encryption:
  enabled: true
  secret-key: ${KESTRA_ENCRYPTION_KEY}  # Set in environment
```

### 3. Use HTTPS in Production

- Use reverse proxy (Nginx, Traefik)
- Or use platform's built-in HTTPS (Railway, Render, Fly.io)

### 4. Restrict Access

- Use firewall rules
- Use authentication tokens
- Limit network access

---

## 🧪 Testing

### Test Workflow Execution

```bash
# Trigger via webhook
curl -X POST http://localhost:8080/api/v1/executions/webhook/autoapplyai/autoapplyai_pipeline/autoapply_webhook \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "John Doe\nSoftware Engineer...",
    "job_description": "Looking for a Python developer..."
  }'
```

### Test Backend Integration

```python
# In backend/main.py, add test endpoint
@app.get("/test/kestra")
async def test_kestra():
    execution_id = await trigger_kestra_workflow(
        resume_text="Test resume",
        job_description="Test JD"
    )
    return {"execution_id": execution_id, "status": "triggered"}
```

---

## 🆘 Troubleshooting

### Kestra Won't Start

**Check logs**:
```bash
docker logs kestra
```

**Common issues**:
- Port 8080 already in use → Change port in config
- Volume permissions → `chmod -R 755 kestra/`
- Memory issues → Increase Docker memory limit

### Workflow Not Found

- Verify workflow is uploaded: `GET /api/v1/flows/autoapplyai/autoapplyai_pipeline`
- Check namespace matches: `namespace: autoapplyai`
- Verify YAML syntax is valid

### Tasks Failing

- Check Python path in config: `python-path: python3`
- Verify backend code is accessible
- Check environment variables are set
- Review task logs in Kestra UI

### Connection Issues

- Verify `KESTRA_URL` is correct
- Check network connectivity
- Verify authentication credentials
- Check CORS settings

---

## 📚 Additional Resources

- [Kestra Documentation](https://kestra.io/docs)
- [Kestra Docker Guide](https://kestra.io/docs/deployment/docker)
- [Kestra API Reference](https://kestra.io/docs/api-reference)
- [Kestra Webhooks](https://kestra.io/docs/plugins/core/triggers/webhook)

---

## ✅ Deployment Checklist

- [ ] Docker/Docker Compose installed
- [ ] Kestra container running
- [ ] Kestra UI accessible
- [ ] Default password changed
- [ ] Workflow uploaded
- [ ] Backend can connect to Kestra
- [ ] Environment variables set
- [ ] Test execution successful
- [ ] Logs accessible
- [ ] Security configured (HTTPS, auth)

---

**Need help?** Check Kestra logs and UI for detailed error messages.


