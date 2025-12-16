# 🚂 Railway 部署完整指南

## 📋 部署前准备

### 1. 检查文件
确保以下文件存在：
- ✅ `Dockerfile` - Docker 配置
- ✅ `cloud/railway.json` - Railway 配置
- ✅ `.env.example` - 环境变量模板
- ✅ `webapp/app.py` - Web 应用
- ✅ `lxw.txt` - 私钥文件（需要上传）

### 2. 准备环境变量
复制以下环境变量列表，部署时需要：

```bash
KALSHI_ENV=demo
KALSHI_API_KEY_ID=95b8c647-f528-4433-8342-7222beb6efdf
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005
FLASK_SECRET_KEY=change-this-to-random-string-$(openssl rand -hex 32)
PYTHONPATH=/app/src
FEE_KIND=taker
POST_ONLY=true
MAX_ORDER_COUNT=10
MAX_POSITION_PER_TICKER=50
POLL_SECONDS=2.0
```

---

## 🚀 部署步骤

### 步骤 1: 提交代码到 GitHub

```bash
# 检查当前状态
git status

# 添加所有文件
git add .

# 提交
git commit -m "Ready for Railway deployment"

# 推送到 GitHub
git push origin main
```

**重要**: 确保代码已推送到 GitHub，Railway 需要从 GitHub 拉取代码。

### 步骤 2: 创建 Railway 账户

1. 访问 https://railway.app
2. 点击 "Start a New Project"
3. 选择 "Login with GitHub"
4. 授权 Railway 访问你的 GitHub 账户

### 步骤 3: 创建新项目

1. 在 Railway Dashboard 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择你的 `kalshi_quant_bot` 仓库
4. Railway 会自动检测 Dockerfile 并开始构建

### 步骤 4: 配置环境变量

在项目页面：

1. 点击项目名称进入项目
2. 点击 "Variables" 标签页
3. 点击 "New Variable" 添加以下变量：

**必需变量：**
```
KALSHI_ENV = demo
KALSHI_API_KEY_ID = 95b8c647-f528-4433-8342-7222beb6efdf
KALSHI_PRIVATE_KEY_PATH = /app/lxw.txt
TICKERS = KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON = {"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD = 0.005
FLASK_SECRET_KEY = [生成随机字符串，见下方]
PYTHONPATH = /app/src
```

**可选变量（使用默认值）：**
```
FEE_KIND = taker
POST_ONLY = true
MAX_ORDER_COUNT = 10
MAX_POSITION_PER_TICKER = 50
POLL_SECONDS = 2.0
```

**生成 FLASK_SECRET_KEY：**
```bash
# 在终端运行
openssl rand -hex 32
# 复制输出的字符串作为 FLASK_SECRET_KEY 的值
```

### 步骤 5: 上传私钥文件

1. 在项目页面点击 "Settings"
2. 滚动到 "Volumes" 部分
3. 点击 "Add Volume"
4. 配置：
   - **Mount Path**: `/app/lxw.txt`
   - **Name**: `private-key` (任意名称)
5. 点击 "Upload" 上传你的 `lxw.txt` 文件
6. 点击 "Add"

### 步骤 6: 配置端口和域名

1. 在项目页面点击 "Settings"
2. 滚动到 "Networking" 部分
3. 点击 "Generate Domain" 生成公共域名
4. Railway 会自动配置端口映射

### 步骤 7: 等待部署完成

1. 在项目页面查看 "Deployments" 标签
2. 等待构建和部署完成（通常 2-5 分钟）
3. 查看日志确认没有错误

### 步骤 8: 验证部署

1. 点击生成的域名访问 Dashboard
2. 应该看到 Kalshi Trading Bot Dashboard
3. 测试 API：
   ```bash
   curl https://your-app.railway.app/api/health
   curl https://your-app.railway.app/api/status
   ```

---

## 🔧 使用 Railway CLI（可选）

### 安装 CLI

```bash
npm i -g @railway/cli
```

### 登录

```bash
railway login
```

### 初始化项目

```bash
railway init
```

### 链接到现有项目

```bash
railway link
```

### 设置环境变量

```bash
railway variables set KALSHI_ENV=demo
railway variables set KALSHI_API_KEY_ID=95b8c647-f528-4433-8342-7222beb6efdf
railway variables set KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
railway variables set TICKERS=KXNEWPOPE-70-PPIZ
railway variables set FLASK_SECRET_KEY=your-secret-key
# ... 设置其他变量
```

### 上传私钥文件

```bash
# 创建 volume
railway volume create

# 挂载文件
railway volume mount /app/lxw.txt

# 上传文件（需要手动操作）
# 在 Railway Dashboard 中上传
```

### 部署

```bash
railway up
```

### 查看日志

```bash
railway logs
railway logs --follow  # 实时日志
```

---

## 📊 监控和日志

### 查看日志

1. **Web Dashboard**: 在项目页面点击 "Deployments" → 选择部署 → "View Logs"
2. **CLI**: `railway logs` 或 `railway logs --follow`

### 监控指标

Railway 提供：
- CPU 使用率
- 内存使用率
- 网络流量
- 请求数

在项目页面的 "Metrics" 标签查看。

---

## 🔄 更新部署

### 自动更新（推荐）

每次推送到 GitHub main 分支，Railway 会自动重新部署：

```bash
git add .
git commit -m "Update code"
git push origin main
```

### 手动触发

1. 在 Railway Dashboard
2. 点击 "Deployments"
3. 点击 "Redeploy"

### 使用 CLI

```bash
railway up
```

---

## 🐛 故障排除

### 问题 1: 构建失败

**检查：**
- Dockerfile 是否正确
- 依赖是否完整
- 查看构建日志

**解决：**
```bash
# 本地测试 Dockerfile
docker build -t kalshi-bot .
docker run -p 5000:5000 kalshi-bot
```

### 问题 2: 应用无法启动

**检查：**
- 环境变量是否全部设置
- 私钥文件是否上传
- 查看运行时日志

**解决：**
```bash
railway logs  # 查看详细错误
```

### 问题 3: 私钥文件找不到

**检查：**
- Volume 是否正确挂载
- 路径是否正确：`/app/lxw.txt`
- 文件是否已上传

**解决：**
1. 在 Settings → Volumes 检查
2. 重新上传文件
3. 重启服务

### 问题 4: WebSocket 连接失败

**检查：**
- Railway 完全支持 WebSocket
- 检查 CORS 配置
- 查看浏览器控制台错误

**解决：**
- Railway 自动处理 WebSocket
- 如果仍有问题，检查代码中的 SocketIO 配置

### 问题 5: 数据库错误

**检查：**
- 文件系统权限
- 数据库路径
- 磁盘空间

**解决：**
- Railway 提供持久化存储
- 数据库文件会保存在 volume 中
- 检查 volume 配置

---

## 💰 费用说明

### Railway 定价

- **Hobby Plan**: $5/月
  - 512MB RAM
  - $5 免费额度
  - 适合个人项目

- **Pro Plan**: $20/月
  - 2GB RAM
  - 更多资源
  - 适合生产环境

### 免费额度

新用户有 $5 免费额度，可以免费使用一个月。

---

## ✅ 部署检查清单

部署前：
- [ ] 代码已推送到 GitHub
- [ ] Dockerfile 已测试
- [ ] 环境变量列表已准备好
- [ ] 私钥文件已准备好
- [ ] Railway 账户已创建

部署中：
- [ ] 项目已创建
- [ ] 环境变量已设置
- [ ] 私钥文件已上传
- [ ] 域名已生成
- [ ] 部署成功

部署后：
- [ ] Dashboard 可以访问
- [ ] API 端点响应正常
- [ ] 健康检查通过
- [ ] 日志正常输出
- [ ] Bot 可以启动

---

## 🎯 快速命令参考

```bash
# 查看状态
railway status

# 查看日志
railway logs --follow

# 查看变量
railway variables

# 设置变量
railway variables set KEY=value

# 部署
railway up

# 打开 Dashboard
railway open
```

---

## 📞 获取帮助

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- 项目 Issues: GitHub Issues

---

## 🎉 部署成功！

部署完成后，你会得到：
- ✅ 公共 URL (例如: `https://your-app.railway.app`)
- ✅ Web Dashboard 访问
- ✅ API 端点可用
- ✅ 自动部署配置

**开始使用你的云端交易机器人吧！** 🚀

