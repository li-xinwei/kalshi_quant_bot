# Railway 部署详细步骤

## 🚀 最快部署方式

### 方法 1: GitHub 集成 (推荐)

1. **准备代码**
   ```bash
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

2. **访问 Railway**
   - 打开 https://railway.app
   - 使用 GitHub 登录

3. **创建项目**
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择你的 `kalshi_quant_bot` 仓库

4. **Railway 会自动检测**
   - 检测到 `Dockerfile` 自动构建
   - 检测到 `railway.json` 使用配置

5. **配置环境变量**
   在项目 Settings → Variables 添加：
   ```
   KALSHI_ENV=demo
   KALSHI_API_KEY_ID=95b8c647-f528-4433-8342-7222beb6efdf
   KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
   TICKERS=KXNEWPOPE-70-PPIZ
   FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
   EDGE_THRESHOLD=0.005
   FLASK_SECRET_KEY=your-random-secret-key-here
   PYTHONPATH=/app/src
   ```

6. **上传私钥文件**
   - 在项目 Settings → Volumes
   - 点击 "Add Volume"
   - Mount Path: `/app/lxw.txt`
   - 上传你的 `lxw.txt` 文件

7. **设置端口**
   - Railway 自动分配端口
   - 在 Settings → Networking
   - 生成 Public Domain

8. **部署完成**
   - 访问生成的 URL
   - Dashboard 应该可以访问了！

### 方法 2: Railway CLI

```bash
# 安装 CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 链接到现有项目或创建新项目
railway link

# 设置环境变量
railway variables set KALSHI_ENV=demo
railway variables set KALSHI_API_KEY_ID=your-key-id
# ... 设置其他变量

# 上传私钥 (需要先创建 volume)
railway volume create
railway volume mount /app/lxw.txt

# 部署
railway up
```

## 🔧 环境变量完整列表

```bash
# 必需变量
KALSHI_ENV=demo
KALSHI_API_KEY_ID=your-api-key-id
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ

# 推荐变量
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005
FLASK_SECRET_KEY=$(openssl rand -hex 32)
PYTHONPATH=/app/src

# 可选变量
FEE_KIND=taker
TAKER_FEE_RATE=0.07
MAKER_FEE_RATE=0.0175
MIN_NET_EV_PER_CONTRACT=0.0
POST_ONLY=true
MAX_ORDER_COUNT=10
MAX_POSITION_PER_TICKER=50
POLL_SECONDS=2.0
```

## 📊 监控和日志

```bash
# 查看日志
railway logs

# 查看实时日志
railway logs --follow

# 查看服务状态
railway status
```

## 🔄 更新部署

```bash
# 推送代码
git push origin main

# Railway 会自动重新部署
# 或手动触发
railway up
```

## 💡 提示

1. **免费试用**: Railway 提供 $5 免费额度
2. **自动部署**: 每次 push 到 main 分支自动部署
3. **环境隔离**: 可以为不同分支创建不同环境
4. **监控**: Railway 提供内置监控和日志

## 🐛 常见问题

### 问题: 构建失败
- 检查 Dockerfile 是否正确
- 查看构建日志: `railway logs`

### 问题: 应用无法启动
- 检查环境变量是否设置
- 确认私钥文件已上传
- 查看运行时日志

### 问题: WebSocket 不工作
- Railway 完全支持 WebSocket
- 检查 CORS 配置
- 确认 SocketIO 正确初始化

## ✅ 部署检查清单

- [ ] 代码已推送到 GitHub
- [ ] Railway 项目已创建
- [ ] 环境变量已设置
- [ ] 私钥文件已上传到 Volume
- [ ] 构建成功
- [ ] 应用运行正常
- [ ] Dashboard 可以访问
- [ ] API 端点响应正常

完成这些步骤后，你的交易机器人就在云端运行了！🎉

