#!/usr/bin/env bash
# Collect the first 5 real pages of each soccerdonna page type into
# samples/pages/<type>/, plus guaranteed anchor pages. Idempotent; re-run to refresh.
set -euo pipefail

BASE='https://www.soccerdonna.de'
UA='soccerdonna-scraper (+research; women-football)'
INDEX='/en/2010/startseite/wettbewerbeDE.html'
OUT='samples/pages'

# Anchors we always want present (used by exact-value tests)
ANCHOR_COMP='/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'
ANCHOR_CLUB='/en/fc-barcelona/kader/verein_1132.html'
ANCHOR_PLAYER='/en/gemma-font/profil/spieler_38461.html'

mkdir -p "$OUT"/{index,competition,club,player,appearance}
get() { curl -fsS -A "$UA" "$BASE$1" -o "$2"; echo "saved $2"; }

# pick first N hrefs matching a regex from a file, anchor first, de-duplicated
pick() { # <htmlfile> <regex> <anchor-href> <n>
  { echo "$3"; grep -oE "$2" "$1" || true; } | awk '!seen[$0]++' | head -n "$4"
}

# 1) Index page
get "$INDEX" "$OUT/index/wettbewerbeDE.html"

# 2) First 5 competitions (ESP1 anchored first). NOTE: index competition links
#    are mostly under /de/; normalize to /en/ so every downstream page and its
#    child links come back in English (verified: /en/ pages emit /en/ links).
mapfile -t COMPS < <(
  { echo "$ANCHOR_COMP";
    grep -oE '/(de|en)/[^"]*wettbewerb_[A-Za-z0-9]+\.html' "$OUT/index/wettbewerbeDE.html" \
      | sed 's#^/de/#/en/#'; } | awk '!seen[$0]++' | head -n 5)
for href in "${COMPS[@]}"; do
  code=$(echo "$href" | grep -oE 'wettbewerb_[A-Za-z0-9]+' | sed 's/wettbewerb_//')
  get "$href" "$OUT/competition/${code}.html"
done

# 3) First 5 clubs from those competition pages (Barcelona anchored first).
#    Convert /startseite/ club hrefs to their /kader/ squad page; force /en/.
CLUB_SRC=$(cat "$OUT"/competition/*.html)
mapfile -t CLUBS < <(printf '%s' "$CLUB_SRC" \
  | grep -oE '/(de|en)/[^"]*verein_[0-9]+\.html' \
  | sed -e 's#^/de/#/en/#' -e 's#/startseite/#/kader/#' \
  | { echo "$ANCHOR_CLUB"; cat; } | awk '!seen[$0]++' | head -n 5)
for href in "${CLUBS[@]}"; do
  id=$(echo "$href" | grep -oE 'verein_[0-9]+')
  get "$href" "$OUT/club/${id}.html"
done

# 4) First 5 players from those squad pages (Gemma Font anchored first); force /en/.
PLAYER_SRC=$(cat "$OUT"/club/*.html)
mapfile -t PLAYERS < <(printf '%s' "$PLAYER_SRC" \
  | grep -oE '/(de|en)/[^"]*spieler_[0-9]+\.html' \
  | sed 's#^/de/#/en/#' \
  | { echo "$ANCHOR_PLAYER"; cat; } | awk '!seen[$0]++' | head -n 5)
for href in "${PLAYERS[@]}"; do
  id=$(echo "$href" | grep -oE 'spieler_[0-9]+')
  get "$href" "$OUT/player/${id}.html"
  # 5) Matching performance-data (appearance) page for each player
  app_href=$(echo "$href" | sed 's#/profil/#/leistungsdaten/#')
  get "$app_href" "$OUT/appearance/${id}.html"
done

echo "Done. Sample counts:"
for d in index competition club player appearance; do
  echo "  $d: $(ls -1 "$OUT/$d" | wc -l)"
done
