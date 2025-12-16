# ⚡ 快速云端部署指南

## 🎯 3分钟部署到 Railway (最简单)

### 步骤 1: 准备代码 (1分钟)
```bash
# 确保代码已提交
git add .
git commit -m "Ready for cloud deployment"
git push origin main
```

### 步骤 2: 创建 Railway 项目 (1分钟)
1. 访问 https://railway.app
2. 点击 "Start a New Project"
3. 选择 "Deploy from GitHub repo"
4. 授权并选择 `kalshi_quant_bot` 仓库

### 步骤 3: 配置环境变量 (1分钟)
在 Railway Dashboard → Variables 添加：

```bash
KALSHI_ENV=demo
KALSHI_API_KEY_ID=95b8c647-f528-4433-8342-7222beb6efdf
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005
FLASK_SECRET_KEY=change-this-to-random-string
PYTHONPATH=/app/src
```

### 步骤 4: 上传私钥
1. 在 Settings → Volumes
2. 点击 "Add Volume"
3. Mount Path: `/app/lxw.txt`
4. 上传 `lxw.txt` 文件

### 步骤 5: 获取 URL
1. 在 Settings → Networking
2. 点击 "Generate Domain"
3. 复制生成的 URL

### ✅ 完成！
访问你的 URL，Dashboard 应该已经运行了！

---

## 🌐 其他平台快速部署

### Render (免费)
1. 访问 https://render.com
2. New → Web Service
3. 连接 GitHub 仓库
4. 配置环境变量
5. Deploy!

### Heroku
```bash
heroku create kalshi-bot
heroku config:set KALSHI_ENV=demo KALSHI_API_KEY_ID=your-key
git push heroku main
```

### DigitalOcean
1. App Platform → Create App
2. 连接 GitHub
3. 选择 Docker
4. 配置环境变量
5. Deploy!

---

## 🔑 必需的环境变量

```bash
KALSHI_ENV=demo                    # 或 prod
KALSHI_API_KEY_ID=your-key-id     # 你的 API Key
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt  # 私钥路径
TICKERS=KXNEWPOPE-70-PPIZ         # 交易标的
FLASK_SECRET_KEY=random-string    # Flask 密钥
```

---

## 📱 部署后访问

1. **Dashboard**: `https://your-app-url.com`
2. **API 状态**: `https://your-app-url.com/api/status`
3. **健康检查**: `https://your-app-url.com/api/health`

---

## 🐛 问题排查

### 应用无法启动
```bash
# 查看日志
railway logs  # Railway
render logs   # Render
heroku logs   # Heroku
```

### 私钥文件问题
- 确认文件路径正确: `/app/lxw.txt`
- 检查文件权限
- 验证文件内容

### 环境变量问题
- 检查所有必需变量是否设置
- 确认 JSON 格式正确
- 验证变量值没有多余空格

---

## 💡 推荐配置

**生产环境建议:**
- 使用 `KALSHI_ENV=prod` (真实交易)
- 设置强密码的 `FLASK_SECRET_KEY`
- 启用 HTTPS
- 设置访问限制

**测试环境建议:**
- 使用 `KALSHI_ENV=demo` (演示环境)
- 小金额测试
- 监控日志

---

## 🎉 部署成功！

你的交易机器人现在在云端运行了！

访问 Dashboard 开始监控和交易。

