#!/bin/bash

# Eval-Loop für Build 1: schickt alle 30 Tickets durch die Pipeline
# und loggt Latency + HTTP-Status in eine lokale CSV.
# Sheet-Output (Severity, Tier etc.) wird von n8n geschrieben.

WEBHOOK_URL="https://buildersbuilding.app.n8n.cloud/webhook/support-triage-v1"
TICKETS_DIR="test-data/tickets"
OUTPUT_CSV="eval-results/eval_v1_$(date +%Y%m%d_%H%M%S).csv"

mkdir -p eval-results

# CSV-Header
echo "ticket_id,http_status,latency_ms,timestamp" > "$OUTPUT_CSV"

# Loop durch alle Ticket-Files
for ticket_file in "$TICKETS_DIR"/ticket_*.json; do
    ticket_id=$(basename "$ticket_file" .json)
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo "→ Sending $ticket_id ..."
    
    # Latency messen: Start-Zeit in Millisekunden (macOS-kompatibel via Python)
    start_ms=$(python3 -c 'import time; print(int(time.time()*1000))')
    
    # curl-Request, nur HTTP-Status zurück
    http_status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        --data @"$ticket_file")
    
    # End-Zeit
    end_ms=$(python3 -c 'import time; print(int(time.time()*1000))')
    latency_ms=$((end_ms - start_ms))
    
    # Eine Zeile pro Ticket in CSV
    echo "$ticket_id,$http_status,$latency_ms,$timestamp" >> "$OUTPUT_CSV"
    
    echo "  ✓ status=$http_status, latency=${latency_ms}ms"
    
    # 1 Sekunde Pause zwischen Requests
    sleep 1
done

echo ""
echo "✅ Eval-Run fertig. Ergebnisse: $OUTPUT_CSV"
echo "   $(wc -l < "$OUTPUT_CSV") Zeilen (inkl. Header)."