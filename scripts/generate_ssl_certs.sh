#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, replace these with real certificates from Let's Encrypt or your CA

set -e

SSL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/nginx/ssl"
mkdir -p "$SSL_DIR"

echo "==================================================================="
echo "Generating self-signed SSL certificates for Tria AIBPO..."
echo "==================================================================="

# Generate private key and certificate
openssl req -x509 \
    -nodes \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "$SSL_DIR/tria.key" \
    -out "$SSL_DIR/tria.crt" \
    -subj "/C=SG/ST=Singapore/L=Singapore/O=Tria AIBPO/OU=Development/CN=tria.local" \
    -addext "subjectAltName=DNS:tria.local,DNS:localhost,DNS:*.tria.local,IP:127.0.0.1"

echo ""
echo "✓ SSL certificates generated successfully!"
echo "  Certificate: $SSL_DIR/tria.crt"
echo "  Private Key: $SSL_DIR/tria.key"
echo ""
echo "Note: These are self-signed certificates for DEVELOPMENT only."
echo "For PRODUCTION, use certificates from a trusted CA (e.g., Let's Encrypt)."
echo ""
