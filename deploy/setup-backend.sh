#!/bin/bash
# AI Product Factory - Backend Deployment Script for Oracle Cloud ARM VM
# Usage: bash setup-backend.sh
set -euo pipefail

APP_DIR="/opt/ai-product-factory"
DATA_DIR="/data"
REPO_URL="https://github.com/groupsmix/poster-digital-auto.git"

echo "=== AI Product Factory - Backend Setup ==="

# 1. System updates & dependencies
echo "[1/8] Installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx git curl

# 2. Install Poetry
echo "[2/8] Installing Poetry..."
if ! command -v poetry &>/dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Create data directory for SQLite
echo "[3/8] Setting up data directory..."
sudo mkdir -p "$DATA_DIR"
sudo chown root:root "$DATA_DIR"

# 4. Clone or update the repo
echo "[4/8] Setting up application..."
if [ -d "$APP_DIR" ]; then
    echo "App directory exists, pulling latest..."
    cd "$APP_DIR"
    git pull origin main
else
    sudo mkdir -p "$APP_DIR"
    sudo chown root:root "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# 5. Set up Python virtual environment and install dependencies
echo "[5/8] Installing Python dependencies..."
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
poetry install --no-interaction

# 6. Set up systemd service
echo "[6/8] Setting up systemd service..."
sudo cp deploy/systemd/ai-product-factory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-product-factory
sudo systemctl restart ai-product-factory

# 7. Set up nginx
echo "[7/8] Setting up nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp deploy/nginx/ai-product-factory.conf /etc/nginx/sites-available/ai-product-factory
sudo ln -sf /etc/nginx/sites-available/ai-product-factory /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 8. Set up cron job for daily AI limit reset at midnight UTC
echo "[8/8] Setting up cron job for daily limit reset..."
(crontab -l 2>/dev/null | grep -v "ai-status/reset"; echo "0 0 * * * curl -s -X POST http://127.0.0.1:8000/api/ai-status/reset > /dev/null 2>&1") | crontab -

echo ""
echo "=== Setup Complete ==="
echo "Backend running at http://localhost:8000"
echo "Nginx proxy active on port 80"
echo ""
echo "Next steps:"
echo "  1. Create .env file: sudo nano $APP_DIR/.env"
echo "  2. Set up SSL: sudo certbot --nginx -d YOUR_DOMAIN"
echo "  3. Test: curl http://localhost:8000/healthz"
