# 🚂 Railway 部署 - 从这里开始

## ⚡ 5分钟快速部署

### 第1步: 提交代码 (1分钟)

```bash
# 添加所有文件
git add .

# 提交
git commit -m "Ready for Railway deployment"

# 推送到 GitHub
git push origin main
```

### 第2步: 创建 Railway 项目 (2分钟)

1. **访问 Railway**
   - 打开 https://railway.app
   - 点击 "Start a New Project"
   - 选择 "Login with GitHub"

2. **部署项目**
   - 选择 "Deploy from GitHub repo"
   - 选择 `kalshi_quant_bot` 仓库
   - Railway 会自动开始构建

### 第3步: 配置环境变量 (1分钟)

在 Railway Dashboard → **Variables** 标签页，添加以下变量：

**复制这些变量（从 railway-env-vars.txt）：**

```
KALSHI_ENV=demo
KALSHI_API_KEY_ID=95b8c647-f528-4433-8342-7222beb6efdf
KALSHI_PRIVATE_KEY_PATH=/app/lxw.txt
TICKERS=KXNEWPOPE-70-PPIZ
FAIR_PROBS_JSON={"KXNEWPOPE-70-PPIZ": 0.995}
EDGE_THRESHOLD=0.005
FLASK_SECRET_KEY=840c9960892dee4e79dfe5a6bda715ad99d9a6a32d17e233ff3ebe6aed9c3b1c
PYTHONPATH=/app/src
```

**快速复制方法：**
```bash
# 查看所有变量
cat railway-env-vars.txt
```

### 第4步: 上传私钥文件 (1分钟)

1. 在 Railway Dashboard → **Settings**
2. 滚动到 **Volumes** 部分
3. 点击 **"Add Volume"**
4. 配置：
   - **Mount Path**: `/app/lxw.txt`
   - **Name**: `private-key` (任意名称)
5. 点击 **"Upload"** 上传 `lxw.txt` 文件
6. 点击 **"Add"**

### 第5步: 生成域名并等待部署 (1分钟)

1. 在 **Settings** → **Networking**
2. 点击 **"Generate Domain"**
3. 等待部署完成（2-5分钟）
4. 复制生成的 URL

### ✅ 完成！

访问你的 URL，Dashboard 应该已经运行了！

---

## 📋 详细步骤

如果需要更详细的说明，查看：
- **完整指南**: `RAILWAY_DEPLOY.md`
- **检查清单**: `railway-deploy-checklist.md`
- **环境变量**: `railway-env-vars.txt`

---

## 🔍 验证部署

部署完成后，测试：

```bash
# 替换为你的 Railway URL
YOUR_URL="https://your-app.railway.app"

# 健康检查
curl $YOUR_URL/api/health

# 状态检查
curl $YOUR_URL/api/status

# 访问 Dashboard
open $YOUR_URL
```

---

## 🐛 遇到问题？

1. **查看日志**: Railway Dashboard → Deployments → View Logs
2. **检查环境变量**: 确认所有变量都已设置
3. **验证私钥**: 确认文件已上传到 Volume
4. **查看文档**: `RAILWAY_DEPLOY.md` 中的故障排除部分

---

## 🎯 下一步

部署成功后：
1. ✅ 访问 Dashboard
2. ✅ 点击 "Start Bot"
3. ✅ 监控交易
4. ✅ 查看订单
5. ✅ 分析性能

**开始部署吧！** 🚀

