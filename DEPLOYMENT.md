# Deployment Guide

## 🚀 Web Dashboard Deployment

### Prerequisites

- Docker and Docker Compose installed
- Kalshi API credentials configured in `.env`

### Quick Start

1. **Build and run with Docker Compose:**
```bash
docker-compose up -d
```

2. **Access the dashboard:**
Open your browser to `http://localhost:5000`

3. **View logs:**
```bash
docker-compose logs -f
```

### Manual Deployment

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r webapp/requirements.txt
```

#### 2. Configure Environment

Ensure `.env` file is configured with:
- `KALSHI_API_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH`
- `KALSHI_ENV` (demo or prod)
- `TICKERS`
- Other configuration options

#### 3. Run Web Application

```bash
cd webapp
python app.py
```

Or using Flask:
```bash
export FLASK_APP=webapp/app.py
flask run --host=0.0.0.0 --port=5000
```

### Production Deployment

#### Using Docker

1. **Build production image:**
```bash
docker build -t kalshi-bot:latest .
```

2. **Run container:**
```bash
docker run -d \
  --name kalshi-bot \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/lxw.txt:/app/lxw.txt:ro \
  --restart unless-stopped \
  kalshi-bot:latest
```

#### Using Systemd (Linux)

Create `/etc/systemd/system/kalshi-bot.service`:

```ini
[Unit]
Description=Kalshi Trading Bot Web Dashboard
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/kalshi_quant_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python -m webapp.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kalshi-bot
sudo systemctl start kalshi-bot
```

### Environment Variables

Set these in `.env` or as environment variables:

- `FLASK_SECRET_KEY`: Secret key for Flask sessions (change in production!)
- `FLASK_ENV`: `development` or `production`
- `KALSHI_API_KEY_ID`: Your Kalshi API key ID
- `KALSHI_PRIVATE_KEY_PATH`: Path to private key file
- `KALSHI_ENV`: `demo` or `prod`
- `TICKERS`: Comma-separated list of tickers

### Security Considerations

1. **Change Flask Secret Key:**
```bash
export FLASK_SECRET_KEY=$(openssl rand -hex 32)
```

2. **Use HTTPS in production:**
   - Use a reverse proxy (nginx) with SSL
   - Or use a service like Cloudflare

3. **Firewall:**
   - Only expose port 5000 to trusted networks
   - Use VPN or SSH tunnel for remote access

### Reverse Proxy Setup (Nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring

The dashboard includes built-in health checks at `/api/health`.

For external monitoring:
```bash
curl http://localhost:5000/api/health
```

### Troubleshooting

1. **Check logs:**
```bash
docker-compose logs kalshi-bot
# or
tail -f logs/kalshi_bot.log
```

2. **Check database:**
```bash
sqlite3 kalshi_bot.db "SELECT COUNT(*) FROM orders;"
```

3. **Test API:**
```bash
curl http://localhost:5000/api/status
```

### Backup

Important files to backup:
- `kalshi_bot.db` - Database
- `logs/` - Log files
- `.env` - Configuration (keep secure!)
- `lxw.txt` - Private key (keep secure!)

### Updates

To update the application:

```bash
# Pull latest code
git pull

# Rebuild Docker image
docker-compose build

# Restart services
docker-compose up -d
```

