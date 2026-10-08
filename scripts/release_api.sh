#!/usr/bin/env bash
# Single-process, no-build rollout for the existing eap-demo.service.
# Usage: release_api.sh check|deploy EXPECTED_FULL_GIT_SHA
set -euo pipefail

mode="${1:-}"
expected="${2:-}"
app_dir="/root/gpt/enterprise-agent-platform"
service="eap-demo.service"
case "$mode" in check|deploy) ;; *) echo "usage: $0 check|deploy EXPECTED_SHA" >&2; exit 2;; esac
[[ "$expected" =~ ^[0-9a-f]{40}$ ]] || { echo "Full 40-character Git SHA required" >&2; exit 2; }
cd "$app_dir"
current="$(git rev-parse HEAD)"
[[ "$current" == "$expected" ]] || { echo "Working checkout SHA mismatch" >&2; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo "Tracked checkout has uncommitted changes" >&2; exit 1; }
systemctl is-active --quiet "$service" || { echo "Demo service is not active" >&2; exit 1; }

available_kb="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
[[ "$available_kb" -ge 350000 ]] || { echo "Not enough available memory: ${available_kb}KB" >&2; exit 1; }
load="$(awk '{print $1}' /proc/loadavg)"
awk -v x="$load" 'BEGIN {exit !(x < 1.0)}' || { echo "Host load too high: $load" >&2; exit 1; }
disk_kb="$(df -Pk "$app_dir" | awk 'NR==2 {print $4}')"
[[ "$disk_kb" -ge 1048576 ]] || { echo "Less than 1 GiB free disk" >&2; exit 1; }

# Match the current systemd service runtime, without starting another app.
PYTHONPATH="$app_dir:/root/.cache/eapdeps" /usr/bin/python3 -c '
import fastapi, pydantic, sqlalchemy, httpx
from app.modules.tools.mcp_service import mcp_service
from app.modules.tools.openapi_service import openapi_service
print("Systemd Python imports: OK")
'

# Existing SQLite store must have the required tables before restart.
# DO NOT run alembic upgrade blindly: legacy stores may lack an alembic_version.
"$app_dir/.venv/bin/python" -c '
from sqlalchemy import inspect
from app.modules.agents.db import engine
from app.core.config import get_settings
url = get_settings().platform_database_url
if not url.startswith("sqlite"):
    raise SystemExit("Expected existing SQLite platform DB; manual migration required for other DBs")
existing = set(inspect(engine).get_table_names())
required = {"agents", "agent_versions", "tools", "agent_tools", "mcp_servers", "openapi_services"}
if not required.issubset(existing):
    raise SystemExit("Platform schema does not have required tables; migration must be reviewed separately")
print("Platform SQLite schema: required tables present")
'
echo "Preflight passed: SHA=$current; MemAvailable=${available_kb}KB; load=$load; free_disk=${disk_kb}KB"

if [[ "$mode" == check ]]; then exit 0; fi

# Serialize releases; do not force through a concurrent rollout.
exec 9>/run/lock/eap-release.lock
flock -n 9 || { echo "Another release is already running" >&2; exit 1; }

# Back up small local stores using sqlite3's online backup API. Do not
# modify or migrate databases during this release.
backup_dir="$app_dir/data/release-backups/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$backup_dir"
EAP_BACKUP_DIR="$backup_dir" "$app_dir/.venv/bin/python" -c '
import os, sqlite3
from pathlib import Path
base = Path("data")
destination = Path(os.environ["EAP_BACKUP_DIR"])
for name in ("platform_resources.db", "platform.db", "knowledge.db"):
    source = base / name
    if not source.exists():
        continue
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as origin:
        with sqlite3.connect(destination / name) as backup:
            origin.backup(backup)
print("SQLite backups completed")
'

# No pip, npm, Docker, worker scaling, or build here.
systemctl restart "$service"
for attempt in 1 2 3 4 5; do
  if curl --fail --silent --show-error --max-time 3 \
    -o /dev/null http://127.0.0.1:18080/health/ready; then
    echo "Health ready after restart"
    exit 0
  fi
  sleep 2
done
echo "Release restart did not become ready; manual intervention required" >&2
exit 1
