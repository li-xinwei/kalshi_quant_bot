# ✅ Railway 部署检查清单

## 📝 部署前准备

### 1. 代码准备
- [ ] 所有文件已提交到 Git
- [ ] 代码已推送到 GitHub
- [ ] Dockerfile 存在且正确
- [ ] `cloud/railway.json` 存在

### 2. 文件检查
```bash
# 运行检查
ls -la Dockerfile
ls -la cloud/railway.json
ls -la webapp/app.py
ls -la lxw.txt
```

### 3. 环境变量准备
- [ ] 已复制 `railway-env-vars.txt` 中的变量
- [ ] FLASK_SECRET_KEY 已生成
- [ ] 所有必需变量已准备好

---

## 🚀 部署步骤

### 步骤 1: GitHub 推送
```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```
- [ ] 代码已推送

### 步骤 2: Railway 账户
- [ ] 访问 https://railway.app
- [ ] 使用 GitHub 登录
- [ ] 账户已创建

### 步骤 3: 创建项目
- [ ] 点击 "New Project"
- [ ] 选择 "Deploy from GitHub repo"
- [ ] 选择 `kalshi_quant_bot` 仓库
- [ ] 项目已创建

### 步骤 4: 配置环境变量
在 Railway Dashboard → Variables：

**必需变量（从 railway-env-vars.txt 复制）：**
- [ ] `KALSHI_ENV` = demo
- [ ] `KALSHI_API_KEY_ID` = 95b8c647-f528-4433-8342-7222beb6efdf
- [ ] `KALSHI_PRIVATE_KEY_PATH` = /app/lxw.txt
- [ ] `TICKERS` = KXNEWPOPE-70-PPIZ
- [ ] `FAIR_PROBS_JSON` = {"KXNEWPOPE-70-PPIZ": 0.995}
- [ ] `EDGE_THRESHOLD` = 0.005
- [ ] `FLASK_SECRET_KEY` = 840c9960892dee4e79dfe5a6bda715ad99d9a6a32d17e233ff3ebe6aed9c3b1c
- [ ] `PYTHONPATH` = /app/src

**可选变量：**
- [ ] `FEE_KIND` = taker
- [ ] `POST_ONLY` = true
- [ ] `MAX_ORDER_COUNT` = 10
- [ ] `MAX_POSITION_PER_TICKER` = 50
- [ ] `POLL_SECONDS` = 2.0

### 步骤 5: 上传私钥文件
在 Railway Dashboard → Settings → Volumes：

- [ ] 点击 "Add Volume"
- [ ] Mount Path: `/app/lxw.txt`
- [ ] 上传 `lxw.txt` 文件
- [ ] Volume 已创建

### 步骤 6: 生成域名
在 Railway Dashboard → Settings → Networking：

- [ ] 点击 "Generate Domain"
- [ ] 域名已生成
- [ ] 复制域名 URL

### 步骤 7: 等待部署
- [ ] 查看 Deployments 标签
- [ ] 构建成功（绿色 ✓）
- [ ] 部署成功（绿色 ✓）
- [ ] 无错误日志

### 步骤 8: 验证部署
- [ ] 访问 Dashboard URL
- [ ] 页面正常加载
- [ ] 测试 API: `curl https://your-app.railway.app/api/health`
- [ ] 测试状态: `curl https://your-app.railway.app/api/status`

---

## 🔍 验证命令

### 测试健康检查
```bash
curl https://your-app.railway.app/api/health
```

### 测试状态
```bash
curl https://your-app.railway.app/api/status
```

### 测试市场数据
```bash
curl https://your-app.railway.app/api/markets
```

---

## 🐛 常见问题检查

### 构建失败？
- [ ] 检查 Dockerfile
- [ ] 查看构建日志
- [ ] 确认依赖正确

### 应用无法启动？
- [ ] 检查环境变量
- [ ] 验证私钥文件路径
- [ ] 查看运行时日志

### 私钥文件找不到？
- [ ] 检查 Volume 挂载
- [ ] 确认路径: `/app/lxw.txt`
- [ ] 重新上传文件

### WebSocket 不工作？
- [ ] Railway 支持 WebSocket
- [ ] 检查 CORS 配置
- [ ] 查看浏览器控制台

---

## 📊 部署后检查

- [ ] Dashboard 可以访问
- [ ] API 端点响应正常
- [ ] 健康检查通过
- [ ] 日志正常输出
- [ ] Bot 可以启动（点击 Start Bot）
- [ ] 订单可以查看
- [ ] 市场数据正常显示

---

## 🎉 部署完成！

如果所有项目都打勾，恭喜！你的交易机器人已成功部署到 Railway！

**下一步：**
1. 访问 Dashboard
2. 点击 "Start Bot"
3. 开始监控交易

---

## 📞 需要帮助？

- 查看详细文档: `RAILWAY_DEPLOY.md`
- Railway Docs: https://docs.railway.app
- 查看日志: Railway Dashboard → Deployments → View Logs

