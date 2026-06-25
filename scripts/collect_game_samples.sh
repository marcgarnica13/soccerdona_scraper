#!/usr/bin/env bash
# Collect game-branch samples (matchday overviews, match reports, lineup pages)
# into samples/pages/{matchday,game,lineup}/, plus guaranteed anchors. Idempotent.
set -euo pipefail

BASE='https://www.soccerdonna.de'
UA='soccerdonna-scraper (+research; women-football)'
OUT='samples/pages'
START='/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'   # ESP1 competition

mkdir -p "$OUT"/{matchday,game,lineup}
get() { curl -fsS -A "$UA" "$BASE$1" -o "$2"; echo "saved $2"; }

# 1) Find the current matchday-overview link on the competition startseite, e.g.
#    /en/.../spieltagsuebersicht/wettbewerb_ESP1_2025_30.html
curl -fsS -A "$UA" "$BASE$START" -o /tmp/_scd_start.html
CUR=$(grep -oE '/en/[^"]*spieltagsuebersicht/wettbewerb_[A-Z0-9]+_[0-9]+_[0-9]+\.html' /tmp/_scd_start.html | head -1)
echo "current matchday overview: $CUR"
CODE=$(echo "$CUR" | grep -oE 'wettbewerb_[A-Z0-9]+' | sed 's/wettbewerb_//')
SEASON=$(echo "$CUR" | grep -oE '_[0-9]+_[0-9]+\.html' | grep -oE '[0-9]+' | head -1)
MD=$(echo "$CUR" | grep -oE '_[0-9]+\.html' | grep -oE '[0-9]+')
SLUG=$(echo "$CUR" | sed -E 's#^/en/([^/]+)/.*#\1#')
echo "code=$CODE season=$SEASON current_matchday=$MD slug=$SLUG"

# 2) Collect 5 matchday-overview pages: current + the 4 prior matchdays.
for i in 0 1 2 3 4; do
  n=$((MD - i)); [ "$n" -lt 1 ] && continue
  href="/en/${SLUG}/spieltagsuebersicht/wettbewerb_${CODE}_${SEASON}_${n}.html"
  get "$href" "$OUT/matchday/${CODE}_${SEASON}_${n}.html"
done

# 3) Collect 5 match reports from the current matchday overview (+ anchor 153373).
mapfile -t GAME_IDS < <(
  { echo "153373";
    grep -oE 'spielbericht_[0-9]+\.html' "$OUT/matchday/${CODE}_${SEASON}_${MD}.html" \
      | grep -oE '[0-9]+'; } | awk '!seen[$0]++' | head -n 5)
for id in "${GAME_IDS[@]}"; do
  # Slug doesn't matter — the report loads by id.
  get "/en/x/index/spielbericht_${id}.html"        "$OUT/game/spielbericht_${id}.html"
  # 4) Matching lineup (aufstellung) page for the same game.
  get "/en/x/aufstellung/spielbericht_${id}.html"  "$OUT/lineup/spielbericht_${id}.html"
done

echo "Done. Sample counts:"
for d in matchday game lineup; do echo "  $d: $(ls -1 "$OUT/$d" | wc -l)"; done
