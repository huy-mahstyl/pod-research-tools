#!/bin/bash
PYTHON=/usr/local/bin/python3
DIR=/Users/mac/Desktop/pod-research-tools
cd "$DIR"

echo "══════════════════════════════════════════════════"
echo "  💡 IDEA GENERATOR — Quick Run                  "
echo "  Trends + Reddit + Etsy → Fresh ideas only!     "
echo "══════════════════════════════════════════════════"
echo ""
echo "  ℹ️  Hệ thống tự động lọc ideas đã thấy trong 7 ngày"
echo "  💡 Để reset lịch sử: chạy với flag --reset"
echo ""
"$PYTHON" idea_generator.py "$@"
