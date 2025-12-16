#!/bin/bash
# Railway 快速部署脚本

echo "🚂 Railway 部署准备检查"
echo "========================"
echo ""

# 检查必需文件
echo "📁 检查文件..."
files=("Dockerfile" "cloud/railway.json" "webapp/app.py" "lxw.txt")
all_ok=true

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
        all_ok=false
    fi
done

echo ""

# 检查 Git 状态
echo "📦 检查 Git 状态..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "  ✅ Git 仓库已初始化"
    
    # 检查是否有未提交的更改
    if [ -n "$(git status --porcelain)" ]; then
        echo "  ⚠️  有未提交的更改"
        echo ""
        echo "建议运行:"
        echo "  git add ."
        echo "  git commit -m 'Ready for Railway deployment'"
        echo "  git push origin main"
    else
        echo "  ✅ 所有更改已提交"
    fi
    
    # 检查远程仓库
    if git remote get-url origin > /dev/null 2>&1; then
        echo "  ✅ GitHub 远程仓库已配置"
        echo "  📍 $(git remote get-url origin)"
    else
        echo "  ⚠️  未配置 GitHub 远程仓库"
        echo ""
        echo "建议运行:"
        echo "  git remote add origin https://github.com/your-username/kalshi_quant_bot.git"
        echo "  git push -u origin main"
    fi
else
    echo "  ❌ 未初始化 Git 仓库"
    all_ok=false
fi

echo ""

# 检查环境变量文件
echo "🔐 检查环境变量配置..."
if [ -f "railway-env-vars.txt" ]; then
    echo "  ✅ railway-env-vars.txt 存在"
    echo "  📋 包含 $(grep -c '^[A-Z]' railway-env-vars.txt) 个环境变量"
else
    echo "  ⚠️  railway-env-vars.txt 不存在"
fi

echo ""

# 总结
if [ "$all_ok" = true ]; then
    echo "✅ 所有检查通过！"
    echo ""
    echo "🚀 下一步："
    echo "1. 访问 https://railway.app"
    echo "2. 登录并创建新项目"
    echo "3. 选择 'Deploy from GitHub repo'"
    echo "4. 选择你的仓库"
    echo "5. 配置环境变量（参考 railway-env-vars.txt）"
    echo "6. 上传私钥文件到 Volume"
    echo "7. 生成域名并等待部署"
    echo ""
    echo "📖 详细步骤请查看: RAILWAY_DEPLOY.md"
else
    echo "❌ 请先解决上述问题"
    exit 1
fi

