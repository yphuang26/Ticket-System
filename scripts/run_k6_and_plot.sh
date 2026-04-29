#!/bin/bash
set -e

case "$1" in
  nginx)      SCRIPT="test_nginx_rate_limit.js" ;;
  backend)    SCRIPT="test_backend_capacity.js" ;;
  breakpoint) SCRIPT="test_backend_ramp_to_breakpoint.js" ;;
  oversell)   SCRIPT="test_oversell.js" ;;
  *)
    echo "Usage: bash scripts/run_k6_and_plot.sh [nginx|backend|breakpoint|oversell]"
    exit 1
    ;;
esac

echo "▶  Starting k6 load test: $1..."
docker compose run --rm k6 run /code/scripts/k6/$SCRIPT

echo ""
echo "▶  Generating plot..."
docker compose run --rm -e K6_TEST=$1 plotter

echo ""
echo "✓  Done. Open k6_$1_result.png"
