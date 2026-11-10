# restore.ps1 - rebuild a machine from .\backup\
#   powershell -ExecutionPolicy Bypass -File .\restore.ps1
#
# Prerequisites: .env exists with the SAME N8N_ENCRYPTION_KEY that was used
# when the backup was taken, and `docker compose up -d` has been run once so
# the containers exist.

$ErrorActionPreference = "Stop"

if (-not (Test-Path .\backup\workflows.json)) {
    Write-Error "No .\backup\workflows.json found - nothing to restore."
}

Write-Host "[1/3] Importing n8n workflows..."
docker exec solar_n8n n8n import:workflow --input=/backup/workflows.json

if (Test-Path .\backup\credentials.json) {
    Write-Host "[2/3] Importing n8n credentials..."
    docker exec solar_n8n n8n import:credentials --input=/backup/credentials.json
} else {
    Write-Host "[2/3] No credentials.json - re-enter the Odoo, SMTP and Groq credentials by hand."
}

if (Test-Path .\backup\odoo.sql) {
    Write-Host "[3/3] Restoring Odoo database..."
    $dbName = if ($env:ODOO_DB) { $env:ODOO_DB } else { "solar" }
    docker cp .\backup\odoo.sql solar_postgres:/tmp/odoo.sql
    docker exec solar_postgres psql -U odoo -d $dbName -f /tmp/odoo.sql
} else {
    Write-Host "[3/3] No odoo.sql - create the database 'solar', install CRM and create the tag 'Manual review' (see README)."
}

Write-Host ""
Write-Host "Restart n8n so imported workflows load cleanly:  docker compose restart n8n"
