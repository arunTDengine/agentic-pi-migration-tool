#!/usr/bin/env bash
# Publish the exact Houston PI Vision Canvas from this folder.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

python3 scenarios/examples/houston-refinery-pivision/generate-layout.py
./run.sh ingest-folder scenarios/examples/houston-refinery-pivision -o scenarios/houston-refinery-pivision.json

set -a
# shellcheck disable=SC1091
source .env
set +a
export IDMP_API_KEY=

CREATE_FLAG=(--create-new)
if [[ "${1:-}" == "--update" ]]; then
  CREATE_FLAG=()
fi

./run.sh migrate scenarios/houston-refinery-pivision.json "${CREATE_FLAG[@]}" --report reports/houston-refinery-pivision.json
echo
echo "Demo data (keep running in another terminal):"
echo "  python3 scenarios/examples/houston-refinery-pivision/start-demo-data.py"
echo
python3 - <<'PY'
import json
from pathlib import Path
report = json.loads(Path("reports/houston-refinery-pivision.json").read_text())[0]
print("Dashboard:", report["url"])
print("Editor:   ", report["edit_url"])
gen = Path("scenarios/examples/houston-refinery-pivision/generate-layout.py")
text = gen.read_text()
old = None
import re
m = re.search(r"^DASHBOARD_ID = .*$", text, re.M)
if m:
    text = re.sub(r"^DASHBOARD_ID = .*$", f"DASHBOARD_ID = {report['dashboard_id']}", text, count=1, flags=re.M)
    gen.write_text(text)
    print("Stamped DASHBOARD_ID =", report["dashboard_id"], "into generate-layout.py")
PY
