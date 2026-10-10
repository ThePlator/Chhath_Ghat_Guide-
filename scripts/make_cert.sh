#!/usr/bin/env bash
# Make a self-signed HTTPS certificate so phones on the laptop's hotspot can
# use GPS, camera and compass (browsers only allow them on https:// pages).
#
# Usage:  scripts/make_cert.sh <hotspot-ip>      e.g. scripts/make_cert.sh 192.168.137.1
#
# Common hotspot IPs: Windows Mobile Hotspot 192.168.137.1 · macOS Internet
# Sharing 192.168.2.1 · Linux NetworkManager 10.42.0.1. Check with
# `ipconfig` / `ifconfig` / `ip addr`.
set -euo pipefail

IP="${1:-}"
if [[ ! "$IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "Usage: $0 <hotspot-ip>   (for example: $0 192.168.137.1)" >&2
  exit 2
fi
command -v openssl >/dev/null || { echo "openssl not found; install it first." >&2; exit 2; }

cd "$(dirname "$0")/.."
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=Chhath Ghat Guide" \
  -addext "subjectAltName=IP:${IP},IP:127.0.0.1,DNS:localhost" 2>/dev/null
chmod 600 certs/key.pem

cat <<MSG
Certificate written to certs/cert.pem (valid 30 days, for ${IP}).

Next:
  1. In .streamlit/config.toml, uncomment:
       sslCertFile = "certs/cert.pem"
       sslKeyFile  = "certs/key.pem"
  2. streamlit run app.py
  3. On each phone: join the hotspot, open https://${IP}:8501
     and accept the certificate warning once.
MSG
