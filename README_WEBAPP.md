# Kalshi Trading Bot - Web Dashboard

## 🎯 Overview

A modern web dashboard for monitoring and controlling the Kalshi trading bot. Features real-time updates, performance metrics, order management, and system health monitoring.

## ✨ Features

- **Real-time Dashboard**: Live updates via WebSocket
- **Bot Control**: Start/stop bot from web interface
- **Order Management**: View and cancel orders
- **Performance Metrics**: P&L charts, win rate, Sharpe ratio
- **Market Data**: Real-time market prices
- **System Health**: Health checks and monitoring
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access dashboard at: `http://localhost:5000`

### Manual Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r webapp/requirements.txt
```

2. **Run the web app:**
```bash
python -m webapp.app
```

3. **Access dashboard:**
Open `http://localhost:5000` in your browser

## 📊 Dashboard Features

### Bot Status Panel
- Real-time bot status (Running/Stopped)
- Loop count
- Active orders count
- Last update timestamp

### Performance Panel
- Total trades
- Win rate
- Net P&L (with color coding)
- Sharpe ratio

### System Health Panel
- System status
- Database connectivity
- Error rate monitoring

### P&L Chart
- Real-time P&L visualization
- Chart.js powered
- Auto-updates every 5 seconds

### Orders Table
- View all active orders
- Cancel orders with one click
- Order details (ticker, side, price, count)

### Market Data Table
- Real-time market prices
- Bid/ask prices for YES/NO
- Mid prices

## 🔌 API Endpoints

### GET `/api/status`
Get bot status and statistics

### POST `/api/start`
Start the trading bot
```json
{
  "paper_mode": true
}
```

### POST `/api/stop`
Stop the trading bot

### GET `/api/orders`
Get orders (supports `?status=active` and `?ticker=TICKER`)

### POST `/api/orders/<order_id>/cancel`
Cancel a specific order

### POST `/api/orders/cancel-all`
Cancel all active orders

### GET `/api/performance`
Get performance metrics (supports `?days=30`)

### GET `/api/markets`
Get current market data

### GET `/api/health`
Get system health status

## 🔧 Configuration

The web app uses the same `.env` configuration as the main bot. Ensure:
- `KALSHI_API_KEY_ID` is set
- `KALSHI_PRIVATE_KEY_PATH` points to your key file
- `KALSHI_ENV` is set (demo or prod)
- `TICKERS` is configured

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t kalshi-bot:latest .
```

### Run Container
```bash
docker run -d \
  --name kalshi-bot \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  kalshi-bot:latest
```

### Docker Compose
```bash
docker-compose up -d
```

## 🔒 Security

- Change `FLASK_SECRET_KEY` in production
- Use HTTPS in production (nginx reverse proxy)
- Restrict access to trusted networks
- Keep API keys secure

## 📱 Mobile Support

The dashboard is responsive and works on mobile devices. Access from any device on your network.

## 🐛 Troubleshooting

### Bot won't start
- Check `.env` configuration
- Verify API keys are correct
- Check logs: `docker-compose logs` or `tail -f logs/kalshi_bot.log`

### WebSocket connection fails
- Ensure port 5000 is accessible
- Check firewall settings
- Verify Flask-SocketIO is installed

### Database errors
- Check database file permissions
- Ensure `kalshi_bot.db` exists
- Check disk space

## 📈 Monitoring

The dashboard includes built-in monitoring:
- Health checks every 10 loops
- Error rate tracking
- Performance metrics
- System status

Access health endpoint: `curl http://localhost:5000/api/health`

## 🔄 Updates

To update the web app:
```bash
git pull
docker-compose build
docker-compose up -d
```

## 📝 Notes

- The web app runs the bot in a separate thread
- Paper mode is recommended for testing
- All data is persisted to SQLite database
- Logs are saved to `logs/` directory

