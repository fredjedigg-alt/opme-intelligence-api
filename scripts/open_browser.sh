#!/bin/bash
# Espera a OPME Intelligence API responder e abre a interface web no navegador
# padrão. Disparado no login pelo LaunchAgent
# com.fredjedigg.opme-intelligence-open (~/Library/LaunchAgents/) — a própria
# API é mantida viva por com.fredjedigg.opme-intelligence-server.

URL="http://127.0.0.1:8000"

for _ in $(seq 1 40); do
  curl -s -o /dev/null -m 1 "$URL/api/v1/health" && break
  sleep 0.5
done

open "$URL/"
