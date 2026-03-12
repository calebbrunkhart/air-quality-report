#!/bin/bash
# Run this ONCE on your fresh Jetstream2 VM to set everything up
# Usage: bash setup_vm.sh <YOUR_JETSTREAM2_IP>
# The API key is prompted interactively so it never appears in any file or shell history
set -e

SERVER_IP=$1

if [ -z "$SERVER_IP" ]; then
  echo "Usage: bash setup_vm.sh <VM_IP>"
  exit 1
fi

# Prompt for API key without echoing it to the terminal
read -rsp "Enter your AirNow API key: " AIRNOW_KEY
echo
if [ -z "$AIRNOW_KEY" ]; then
  echo "Error: API key cannot be empty."
  exit 1
fi

echo "==> Updating system packages..."
sudo apt-get update -qq && sudo apt-get upgrade -y -qq

echo "==> Installing dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git debian-keyring debian-archive-keyring apt-transport-https curl

echo "==> Installing Caddy..."
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -qq
sudo apt-get install -y caddy

echo "==> Creating app directory..."
sudo mkdir -p /opt/airquality/data /opt/airquality/logs
sudo chown -R exouser:exouser /opt/airquality

echo "==> Cloning repo..."
# Replace with your actual GitHub repo URL
git clone https://github.com/YOUR_USERNAME/air-quality-monitor.git /opt/airquality || true
cd /opt/airquality

echo "==> Creating Python virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

echo "==> Writing .env file..."
cat > /opt/airquality/.env << EOF
AIRNOW_API_KEY=${AIRNOW_KEY}
DB_PATH=/opt/airquality/data/airquality.db
SERVER_IP=${SERVER_IP}
EOF

echo "==> Initialising database..."
./venv/bin/python database.py

echo "==> Installing systemd units..."
sudo cp systemd/airquality.service        /etc/systemd/system/
sudo cp systemd/airquality-poller.service /etc/systemd/system/
sudo cp systemd/airquality-poller.timer   /etc/systemd/system/
sudo systemctl daemon-reload

echo "==> Enabling and starting services..."
sudo systemctl enable --now airquality
sudo systemctl enable --now airquality-poller.timer

echo "==> Configuring Caddy..."
sudo cp Caddyfile /etc/caddy/Caddyfile
sudo sed -i "s/\{\\$SERVER_IP\}/${SERVER_IP}/g" /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy

echo ""
echo "   Setup complete!"
echo "   Dashboard will be available at: https://airquality.${SERVER_IP}.nip.io"
echo "   Run a manual poll:  cd /opt/airquality && ./venv/bin/python poller.py"
echo "   Check dashboard:    sudo systemctl status airquality"
echo "   Check timer:        sudo systemctl list-timers"