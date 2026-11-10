#!/bin/sh
set -eu

: "${REGION:=sa-east-1}"
ORDER_SYNC_QUEUE="${ORDER_SYNC_QUEUE:-olist-orders-${REGION}}"
export ORDER_SYNC_QUEUE

echo "order-sync: region=${REGION} queue=${ORDER_SYNC_QUEUE}"
python /app/worker.py &
trap 'echo "order-sync: dừng sạch"; exit 0' TERM
wait
