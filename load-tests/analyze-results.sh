#!/bin/bash
# Analyze load test results and generate report

set -e

RESULTS_DIR="load-tests/results"
LATEST_RESULT=$(ls -t $RESULTS_DIR/*.json | head -1)

if [ -z "$LATEST_RESULT" ]; then
    echo "No test results found in $RESULTS_DIR"
    exit 1
fi

echo "Analyzing results from: $LATEST_RESULT"
echo ""

# Generate HTML report
artillery report $LATEST_RESULT --output $RESULTS_DIR/report-$(date +%Y%m%d-%H%M%S).html

echo "HTML report generated!"
echo ""

# Extract key metrics using jq
if command -v jq &> /dev/null; then
    echo "=== Performance Summary ==="
    echo ""
    
    echo "Request Rate:"
    jq '.aggregate.rps.mean' $LATEST_RESULT
    echo ""
    
    echo "Response Time (ms):"
    echo "  Min: $(jq '.aggregate.latency.min' $LATEST_RESULT)"
    echo "  Max: $(jq '.aggregate.latency.max' $LATEST_RESULT)"
    echo "  Median: $(jq '.aggregate.latency.median' $LATEST_RESULT)"
    echo "  p95: $(jq '.aggregate.latency.p95' $LATEST_RESULT)"
    echo "  p99: $(jq '.aggregate.latency.p99' $LATEST_RESULT)"
    echo ""
    
    echo "Status Codes:"
    jq '.aggregate.codes' $LATEST_RESULT
    echo ""
    
    echo "Errors:"
    jq '.aggregate.errors' $LATEST_RESULT
    echo ""
    
    # Performance benchmarks
    P95=$(jq '.aggregate.latency.p95' $LATEST_RESULT)
    ERROR_RATE=$(jq '.aggregate.errors | length' $LATEST_RESULT)
    
    echo "=== Performance Benchmarks ==="
    echo ""
    
    if (( $(echo "$P95 < 2000" | bc -l) )); then
        echo "✓ Latency (p95): PASS ($P95 ms < 2000 ms)"
    else
        echo "✗ Latency (p95): FAIL ($P95 ms >= 2000 ms)"
    fi
    
    if [ "$ERROR_RATE" -eq 0 ]; then
        echo "✓ Error Rate: PASS (0 errors)"
    else
        echo "✗ Error Rate: FAIL ($ERROR_RATE errors)"
    fi
else
    echo "Install jq for detailed metrics analysis"
fi

echo ""
echo "Full report available at: $RESULTS_DIR/report-*.html"
