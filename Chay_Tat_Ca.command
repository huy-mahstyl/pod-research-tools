#!/bin/bash
PYTHON=/usr/local/bin/python3
DIR=/Users/mac/Desktop/pod-research-tools
cd "$DIR"

echo "══════════════════════════════════════════════════"
echo "   🚀 POD RESEARCH HUB — Full Intelligence Suite  "
echo "══════════════════════════════════════════════════"
echo ""
echo "  Running 5 tools — Phase 1: Data Collection"
echo ""

# ── PHASE 1: Data Collection (parallel) ──────────────────
(
    echo "  🔄 [1/5] Google Trends (RSS)..."
    "$PYTHON" google_trends.py 2>&1
    echo "  ✅ [1/5] Google Trends DONE"
) &
PID1=$!

(
    sleep 2
    echo "  🔄 [2/5] Trend Alert (Reddit + ESPN)..."
    "$PYTHON" trend_alert.py 2>&1
    echo "  ✅ [2/5] Trend Alert DONE"
) &
PID2=$!

(
    echo "  🔄 [3/5] Store Spy + Google Image Spy..."
    "$PYTHON" multistore_scraper.py 2>&1
    "$PYTHON" google_spy.py 2>&1
    echo "  ✅ [3/5] Store Spy DONE"
) &
PID3=$!

(
    sleep 3
    echo "  🔄 [4/5] Etsy Spy (Bestseller Intelligence)..."
    "$PYTHON" etsy_spy.py 2>&1
    echo "  ✅ [4/5] Etsy Spy DONE"
) &
PID4=$!

# Wait for all data collection to finish
wait $PID1 $PID2 $PID3 $PID4

echo ""
echo "  ── Phase 2: Idea Generation ───────────────────"
echo "  🔄 [5/5] Generating Design Ideas + Gemini Prompts..."
"$PYTHON" idea_generator.py 2>&1
echo "  ✅ [5/5] Idea Generator DONE"

echo ""
echo "══════════════════════════════════════════════════"
echo "  🎉 ALL DONE! Dashboards ready:"
echo "  💡 ideas_dashboard.html  — Design Ideas + Gemini Prompts"
echo "  🛒 etsy_spy.html         — Etsy Bestsellers"
echo "  📊 daily_ideas.html      — Store Spy + Google"
echo "  🔥 trend_alert.html      — Reddit + ESPN"
echo "  📈 google_trends.html    — Keyword Monitor"
echo "══════════════════════════════════════════════════"
