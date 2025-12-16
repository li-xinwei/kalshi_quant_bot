#!/bin/bash
# Universal cloud deployment script

set -e

PLATFORM=${1:-railway}

echo "🚀 Deploying to $PLATFORM..."

case $PLATFORM in
  railway)
    echo "📦 Deploying to Railway..."
    if command -v railway &> /dev/null; then
      railway up
    else
      echo "Install Railway CLI: npm i -g @railway/cli"
      echo "Then run: railway login && railway up"
    fi
    ;;
  
  render)
    echo "📦 Deploying to Render..."
    if [ -f "render.yaml" ]; then
      echo "Push to GitHub and connect to Render dashboard"
      echo "Or use Render CLI: render deploy"
    fi
    ;;
  
  heroku)
    echo "📦 Deploying to Heroku..."
    if command -v heroku &> /dev/null; then
      heroku create kalshi-trading-bot || true
      heroku config:set FLASK_ENV=production
      git push heroku main
    else
      echo "Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
    fi
    ;;
  
  gcp)
    echo "📦 Deploying to Google Cloud..."
    if command -v gcloud &> /dev/null; then
      gcloud app deploy cloud/app.yaml
    else
      echo "Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    fi
    ;;
  
  aws)
    echo "📦 Deploying to AWS..."
    echo "Using AWS ECS/Fargate..."
    docker build -t kalshi-bot:latest .
    # Push to ECR and deploy (requires AWS CLI setup)
    echo "See CLOUD_DEPLOYMENT.md for AWS instructions"
    ;;
  
  *)
    echo "Unknown platform: $PLATFORM"
    echo "Supported: railway, render, heroku, gcp, aws"
    exit 1
    ;;
esac

echo "✅ Deployment initiated!"

