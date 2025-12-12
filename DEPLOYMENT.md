# 🚀 Quick Deployment Guide

> **For Kestra deployment, see [KESTRA_DEPLOYMENT.md](./KESTRA_DEPLOYMENT.md)**

## TL;DR - Fastest Path to Production

### 1. Frontend (Vercel) - 2 minutes
```bash
cd frontend
vercel
# Connect GitHub, deploy
```

### 2. Backend (Railway) - 5 minutes
1. Go to [railway.app](https://railway.app) → Sign up with GitHub
2. New Project → Deploy from GitHub
3. Select your repo → Railway auto-detects Dockerfile
4. Set root directory: `backend`
5. Add env vars (see below)
6. Deploy → Copy URL

### 3. Connect Them - 1 minute
- Vercel: Add `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`
- Railway: Add `ALLOWED_ORIGINS=https://your-frontend.vercel.app`

---

## 📋 Environment Variables

### Backend (Railway/Render)
```env
TOGETHER_API_KEY=your_key_here
API_KEY=your_secret_key
ALLOWED_ORIGINS=https://your-app.vercel.app
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

---

## 🎯 Platform Comparison

| Platform | Free Tier | Ease | Best For |
|----------|-----------|------|----------|
| **Railway** | ✅ $5 credit/month | ⭐⭐⭐⭐⭐ | Hackathons, quick deploys |
| **Render** | ✅ 750 hours/month | ⭐⭐⭐⭐ | Free tier projects |
| **Fly.io** | ✅ Generous | ⭐⭐⭐ | Global edge deployment |
| **Google Cloud Run** | ✅ 2M requests/month | ⭐⭐⭐ | Enterprise scale |

---

## 🔧 Platform-Specific Instructions

### Railway
1. **Sign up**: [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. **Select repo** → Auto-detects Dockerfile
4. **Settings** → **Root Directory**: `backend`
5. **Variables** → Add all env vars
6. **Deploy** → Done!

### Render
1. **Sign up**: [render.com](https://render.com)
2. **New** → **Web Service**
3. **Connect GitHub** → Select repo
4. **Settings**:
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment** → Add vars
6. **Deploy**

### Fly.io
```bash
# Install CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (from backend directory)
cd backend
fly launch
# Follow prompts, select region
# Add secrets: fly secrets set TOGETHER_API_KEY=xxx
```

---

## ✅ Post-Deployment Checklist

- [ ] Backend health check: `curl https://your-backend.railway.app/health`
- [ ] Frontend loads without errors
- [ ] API calls from frontend work
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] Logs accessible and clean

---

## 🆘 Common Issues

**"Backend not found"**
- Check Railway/Render logs
- Verify port 8000 is exposed
- Check environment variables

**"CORS error"**
- Add frontend URL to `ALLOWED_ORIGINS`
- Format: `https://your-app.vercel.app` (no trailing slash)

**"Build failed"**
- Check `requirements.txt` syntax
- Verify Python version (3.9+)
- Check Dockerfile paths

---

## 🔗 Quick Links

- [Railway Dashboard](https://railway.app/dashboard)
- [Render Dashboard](https://dashboard.render.com)
- [Vercel Dashboard](https://vercel.com/dashboard)
- [Fly.io Dashboard](https://fly.io/dashboard)

---

## 💡 Pro Tips

1. **Use Railway for hackathons** - fastest setup
2. **Use Render for free tier** - most generous
3. **Use Fly.io for production** - best performance
4. **Test locally first** - `docker-compose up`
5. **Monitor logs** - catch errors early

---

**Need help?** Check the main README.md deployment section for detailed instructions.
