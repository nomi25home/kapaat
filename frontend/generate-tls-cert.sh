#!/bin/sh
# Runs automatically via nginx's /docker-entrypoint.d/ hook mechanism, before nginx starts.
# Self-signed TLS so Caddy<->nginx traffic isn't plaintext on the LAN. Caddy's route uses
# tls_insecure_skip_verify, so cert identity doesn't matter; only encryption does. Regenerated
# on every container start (no persistent volume for it; a fresh 2048-bit key is instant).
set -e
mkdir -p /etc/nginx/tls
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -keyout /etc/nginx/tls/tls.key -out /etc/nginx/tls/tls.crt \
  -subj /CN=kapaat.home.mihirfamily.com
