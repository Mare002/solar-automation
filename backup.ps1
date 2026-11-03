# backup.ps1 - run from the solar-automation folder while the stack is up.
#   powershell -ExecutionPolicy Bypass -File .\backup.ps1
#
# Writes into .\backup\ :
#   workflows.json    - all n8n workflows (safe to commit)
#   credentials.json  - n8n credentials, still ENCRYPTED (needs N8N_ENCRYPTION_KEY to restore)
#   odoo.sql          - full Odoo database dump
#
# Run this after every session where you change a workflow or the pipeline.
# The last machine was lost with none of this on disk.

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path .\backup | Out-Null

Write-Host "[1/3] Exporting n8n workflows..."
docker exec solar_n8n n8n export:workflow --all --output=/backup/workflows.json

Write-Host "[2/3] Exporting n8n credentials (encrypted)..."
docker exec solar_n8n n8n export:credentials --all --output=/backup/credentials.json

Write-Host "[3/3] Dumping Odoo database..."
# Odoo's DB name is whatever you typed on the first-run setup screen.
$dbName = if ($env:ODOO_DB) { $env:ODOO_DB } else { "solar" }
docker exec solar_postgres pg_dump -U odoo -d $dbName -f /tmp/odoo.sql
docker cp solar_postgres:/tmp/odoo.sql .\backup\odoo.sql

Write-Host ""
Write-Host "Done. Files are in .\backup\"
Write-Host "credentials.json is encrypted with N8N_ENCRYPTION_KEY from .env - useless without it."
Write-Host "Commit workflows.json to git. Keep the key in a password manager, not in the repo."
