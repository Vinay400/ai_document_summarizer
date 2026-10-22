#!/usr/bin/env bash
# Convert REPORT.md to REPORT.pdf.
#
# Pipeline:  REPORT.md --(marked)--> HTML --(headless Edge/Chromium)--> PDF
#
# Requires only Node (for `npx marked`) and Microsoft Edge or Google Chrome.
# No pandoc, no LaTeX, no Python packages.
#
# Usage:  bash tools/build-pdf.sh

set -euo pipefail

# Project root = the parent of this script's directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MD="REPORT.md"
CSS="tools/print.css"
HTML="tools/_report_build.html"
PDF="REPORT.pdf"

[ -f "$MD" ]  || { echo "error: $MD not found in $ROOT" >&2; exit 1; }
[ -f "$CSS" ] || { echo "error: $CSS not found" >&2; exit 1; }

# --- Locate a Chromium-based browser -----------------------------------------
BROWSER=""
for candidate in \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
do
  if [ -f "$candidate" ]; then BROWSER="$candidate"; break; fi
done

if [ -z "$BROWSER" ]; then
  echo "error: no Edge or Chrome found. Install one, or open $HTML and print to PDF manually." >&2
  exit 1
fi

echo "browser: $BROWSER"

# --- 1. Markdown -> HTML body ------------------------------------------------
echo "converting $MD -> HTML ..."
npx --yes marked -i "$MD" -o "tools/_body.html"

# --- 2. Wrap the body with the print stylesheet ------------------------------
{
  echo '<!DOCTYPE html>'
  echo '<html lang="en"><head><meta charset="utf-8">'
  echo '<title>AI Document Summarizer — Project Report</title>'
  echo "<style>$(cat "$CSS")</style>"
  echo '</head><body>'
  cat "tools/_body.html"
  echo '</body></html>'
} > "$HTML"

# --- 3. HTML -> PDF via headless Chromium ------------------------------------
# The file:// URL must be absolute and URL-encoded. The project path contains a
# space ("Minor Project"), and a relative path here silently produces a blank
# PDF, because Chromium resolves it against the filesystem root.
ABS_PATH="$ROOT/$HTML"
WIN_PATH="$(printf '%s' "$ABS_PATH" | sed -E 's|^/([a-zA-Z])/|\1:/|')"
URL_PATH="$(printf '%s' "$WIN_PATH" | sed 's/ /%20/g')"
FILE_URL="file:///$URL_PATH"

echo "printing to $PDF ..."
# A private user-data-dir avoids clashing with an already-running Edge/Chrome,
# which would otherwise swallow the print request and exit without writing.
PROFILE_DIR="${TMPDIR:-/tmp}/md2pdf-profile"
"$BROWSER" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --user-data-dir="$PROFILE_DIR" \
  --print-to-pdf="$ROOT/$PDF" \
  "$FILE_URL" 2>&1 | grep -v "fallback_task_provider\|Every renderer" || true

# --- 4. Tidy up the intermediates -------------------------------------------
rm -f "tools/_body.html" "$HTML"

if [ -f "$PDF" ]; then
  SIZE="$(du -h "$PDF" | cut -f1)"
  echo "done: $PDF ($SIZE)"
else
  echo "error: the PDF was not produced. Open $HTML in a browser and print manually." >&2
  exit 1
fi
