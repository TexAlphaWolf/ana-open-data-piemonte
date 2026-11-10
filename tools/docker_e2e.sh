#!/usr/bin/env bash
# End to end inside the image (read-only root, no capabilities, no network): the ISTAT files that ship in the image are read and
# checked, the report is written and rebuilt exactly from its JSON, the tables are queried, the two implementations are
# compared and the benchmark runs small. Needs Docker. Usage: tools/docker_e2e.sh [image]
set -euo pipefail
IMAGE="${1:-odp}"
VOL="odp-e2e-$$"
TMP="$(mktemp -d)"
trap 'docker volume rm -f "$VOL" >/dev/null 2>&1 || true; rm -rf "$TMP"' EXIT

[ "$(docker run --rm --entrypoint id "$IMAGE" -u)" != 0 ]   # not root
docker volume create "$VOL" >/dev/null
docker run --rm --user 0 -v "$VOL":/data --entrypoint chown "$IMAGE" 10001 /data

RUN=(docker run --rm --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --network none -v "$VOL":/data "$IMAGE")
cat_file() { docker run --rm --entrypoint cat -v "$VOL":/data "$IMAGE" "$1" > "$2"; }

out="$("${RUN[@]}" check-data)"
grep -q '1,180 municipalities, 107 provinces, 20 regions' <<<"$out"
grep -q 'add up to the same population' <<<"$out"

out="$("${RUN[@]}" report --out /data/out)"
grep -q '1,180 municipalities, 4,255,006 residents' <<<"$out"
grep -q 'rank 8 of 20 regions' <<<"$out"
cat_file /data/out/report.json "$TMP/report.json"
grep -q '"kind": "report"' "$TMP/report.json"
cat_file /data/out/report.md "$TMP/report.md"
"${RUN[@]}" render /data/out/report.json -o /data/out/again.md >/dev/null
cat_file /data/out/again.md "$TMP/again.md"
cmp "$TMP/again.md" "$TMP/report.md"                              # the report is rebuilt exactly from the JSON
cat_file /data/out/summary.png "$TMP/summary.png"
[ "$(head -c 4 "$TMP/summary.png" | tail -c 3)" = "PNG" ]

out="$("${RUN[@]}" indicators --top 3)"
grep -q '^006136 Ponzone' <<<"$out"
out="$("${RUN[@]}" comune Biella)"
grep -q 'Biella (096004), province Biella' <<<"$out"

out="$("${RUN[@]}" verify --draws 5)"
grep -q '^8 of 8 comparisons agree with the literal implementation' <<<"$out"

"${RUN[@]}" bench --sizes 200,400 --ref-max 400 --repeat 1 --draws 2 --out /data/bench >/dev/null
cat_file /data/bench/bench.json "$TMP/bench.json"
grep -q '"ok": true' "$TMP/bench.json"

set +e; "${RUN[@]}" check-data --data /data/nope >/dev/null 2>&1; rc=$?; set -e   # a missing folder is exit code 2
[ "$rc" = 2 ]
echo "docker end-to-end: OK"
