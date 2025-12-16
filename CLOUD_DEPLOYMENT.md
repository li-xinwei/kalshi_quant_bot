# ☁️ 云端部署指南

## 🎯 支持的云平台

1. **Railway** (推荐 - 最简单)
2. **Render** (免费套餐)
3. **Heroku** (需要信用卡)
4. **Google Cloud Platform**
5. **AWS** (ECS/Fargate)
6. **DigitalOcean** (App Platform)

---

## 🚀 Railway 部署 (推荐)

### 步骤 1: 准备代码
```bash
# 确保代码已提交到 Git
git add .
git commit -m "Ready for deployment"
git push
```

### 步骤 2: 连接 Railway
1. 访问 https://railway.app
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的仓库

### 步骤 3: 配置环境变量
在 Railway Dashboard 中添加：
```
KALSHI_ENV=demo
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005
FLASK_SECRET_KEY=your-secret-key
```

### 步骤 4: 上传私钥文件
1. 在 Railway 项目设置中
2. 添加文件卷 (Volume)
3. 挂载路径: `/app/lxw.txt`
4. 上传你的私钥文件

### 步骤 5: 部署
Railway 会自动检测 Dockerfile 并部署

### 使用 CLI (可选)
```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

---

## 🌐 Render 部署

### 步骤 1: 创建账户
访问 https://render.com

### 步骤 2: 新建 Web Service
1. 点击 "New +" → "Web Service"
2. 连接 GitHub 仓库
3. 选择仓库和分支

### 步骤 3: 配置
- **Name**: kalshi-trading-bot
- **Environment**: Docker
- **Dockerfile Path**: Dockerfile
- **Docker Context**: . (根目录)
- **Plan**: Free (或 Starter)

### 步骤 4: 环境变量
在 Environment 标签页添加：
```
KALSHI_ENV=demo
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ
FLASK_SECRET_KEY=your-secret-key
```

### 步骤 5: 私钥文件
使用 Render 的 Shell 功能上传：
```bash
# 在 Render Shell 中
echo "YOUR_PRIVATE_KEY_CONTENT" > lxw.txt
```

### 步骤 6: 部署
点击 "Create Web Service" 开始部署

---

## 🟣 Heroku 部署

### 步骤 1: 安装 Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# 或访问 https://devcenter.heroku.com/articles/heroku-cli
```

### 步骤 2: 登录
```bash
heroku login
```

### 步骤 3: 创建应用
```bash
heroku create kalshi-trading-bot
```

### 步骤 4: 配置环境变量
```bash
heroku config:set KALSHI_ENV=demo
heroku config:set KALSHI_API_KEY_ID=your-key-id
heroku config:set TICKERS=KXNEWPOPE-70-PPIZ
heroku config:set FLASK_SECRET_KEY=your-secret-key
```

### 步骤 5: 上传私钥
```bash
# 方法1: 使用 Heroku Config Vars (base64编码)
cat lxw.txt | base64 | heroku config:set PRIVATE_KEY_BASE64="$(cat)"

# 方法2: 使用 Heroku File System (需要插件)
heroku plugins:install heroku-buildpacks
```

### 步骤 6: 部署
```bash
git push heroku main
```

---

## ☁️ Google Cloud Platform 部署

### 步骤 1: 安装 Google Cloud SDK
```bash
# macOS
brew install google-cloud-sdk

# 或访问 https://cloud.google.com/sdk/docs/install
```

### 步骤 2: 初始化项目
```bash
gcloud init
gcloud auth login
```

### 步骤 3: 创建 App Engine 应用
```bash
gcloud app create --region=us-central
```

### 步骤 4: 配置环境变量
编辑 `cloud/app.yaml` 或使用：
```bash
gcloud app deploy cloud/app.yaml --set-env-vars KALSHI_ENV=demo,KALSHI_API_KEY_ID=your-key-id
```

### 步骤 5: 部署
```bash
gcloud app deploy cloud/app.yaml
```

---

## 🟠 AWS 部署 (ECS/Fargate)

### 步骤 1: 创建 ECR 仓库
```bash
aws ecr create-repository --repository-name kalshi-bot
```

### 步骤 2: 构建并推送镜像
```bash
# 登录 ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# 构建镜像
docker build -t kalshi-bot .

# 标记镜像
docker tag kalshi-bot:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/kalshi-bot:latest

# 推送镜像
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/kalshi-bot:latest
```

### 步骤 3: 创建 ECS 任务定义
使用 AWS Console 或 CLI 创建任务定义，配置：
- 镜像: ECR 镜像 URL
- 端口: 5000
- 环境变量: 所有 KALSHI_* 变量
- 内存: 512 MB
- CPU: 256 units

### 步骤 4: 运行任务
```bash
aws ecs run-task --cluster your-cluster --task-definition kalshi-bot
```

---

## 🔵 DigitalOcean App Platform 部署

### 步骤 1: 创建账户
访问 https://www.digitalocean.com

### 步骤 2: 创建 App
1. 进入 App Platform
2. 点击 "Create App"
3. 连接 GitHub 仓库

### 步骤 3: 配置
- **Type**: Web Service
- **Build Command**: (自动检测)
- **Run Command**: `python -m webapp.app`
- **Environment**: Docker

### 步骤 4: 环境变量
添加所有必要的环境变量

### 步骤 5: 部署
点击 "Create Resources"

---

## 🔐 环境变量配置

所有平台都需要这些环境变量：

```bash
# Kalshi API
KALSHI_ENV=demo  # 或 prod
KALSHI_API_KEY_ID=your-api-key-id
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt  # 或使用环境变量

# Trading Config
TICKERS=KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005

# Flask
FLASK_ENV=production
FLASK_SECRET_KEY=your-secret-key-here

# Python
PYTHONPATH=/app/src
```

### 私钥处理方式

#### 方式 1: 环境变量 (Base64)
```bash
# 编码私钥
cat lxw.txt | base64

# 设置为环境变量
PRIVATE_KEY_BASE64=encoded_key_here

# 在代码中解码 (需要修改代码)
```

#### 方式 2: 文件卷 (推荐)
- Railway: 使用 Volumes
- Render: 使用 Shell 上传
- Heroku: 使用 buildpack 或 Config Vars

#### 方式 3: Secrets Manager
- AWS: AWS Secrets Manager
- GCP: Secret Manager
- Azure: Key Vault

---

## 📝 部署前检查清单

- [ ] 代码已提交到 Git
- [ ] `.env` 文件已配置
- [ ] 私钥文件已准备好
- [ ] 环境变量已设置
- [ ] Dockerfile 已测试
- [ ] 端口配置正确 (5000)
- [ ] 健康检查端点可用 (`/api/health`)

---

## 🧪 测试部署

部署后测试：

```bash
# 检查健康状态
curl https://your-app-url.com/api/health

# 检查状态
curl https://your-app-url.com/api/status

# 访问 Dashboard
# 打开浏览器: https://your-app-url.com
```

---

## 🔧 故障排除

### 问题: 应用无法启动
- 检查日志: `railway logs` 或平台日志
- 验证环境变量是否正确
- 确认私钥文件路径正确

### 问题: 数据库错误
- 检查文件系统权限
- 确认数据库路径可写
- 考虑使用外部数据库 (PostgreSQL)

### 问题: WebSocket 连接失败
- 检查平台是否支持 WebSocket
- 验证 CORS 配置
- 检查防火墙设置

### 问题: 内存不足
- 增加实例内存
- 优化代码
- 减少并发连接

---

## 💰 成本估算

### Railway
- **Hobby**: $5/月 (512MB RAM)
- **Pro**: $20/月 (2GB RAM)

### Render
- **Free**: 免费 (有限制)
- **Starter**: $7/月

### Heroku
- **Eco**: $5/月
- **Basic**: $7/月

### GCP
- **App Engine**: 按使用量付费 (~$10-30/月)

### AWS
- **Fargate**: 按使用量付费 (~$15-50/月)

---

## 🚀 快速部署脚本

使用提供的脚本：

```bash
chmod +x cloud/deploy.sh
./cloud/deploy.sh railway  # 或其他平台
```

---

## 📚 更多资源

- Railway Docs: https://docs.railway.app
- Render Docs: https://render.com/docs
- Heroku Docs: https://devcenter.heroku.com
- GCP Docs: https://cloud.google.com/docs

---

## ✅ 推荐方案

**最佳选择**: Railway
- ✅ 最简单
- ✅ Docker 支持
- ✅ 文件卷支持
- ✅ 自动部署
- ✅ 合理的价格

**免费选择**: Render
- ✅ 免费套餐
- ✅ Docker 支持
- ✅ GitHub 集成

选择最适合你需求的平台开始部署！

