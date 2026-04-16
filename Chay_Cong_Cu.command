#!/bin/bash
cd /Users/mac/Desktop/pod-research-tools
echo "=============================================="
echo "  Running Multi-Store Scraper..."
echo "=============================================="
/usr/local/bin/python3 multistore_scraper.py
echo "-----------------------------------"
echo "  Running Google Image Spy (Playwright)..."
echo "=============================================="
/usr/local/bin/python3 google_spy.py
