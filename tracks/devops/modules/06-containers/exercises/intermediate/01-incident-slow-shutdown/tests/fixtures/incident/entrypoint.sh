#!/bin/sh
set -eu

: "${REGION:=sa-east-1}"
ORDER_SYNC_QUEUE="${ORDER_SYNC_QUEUE:-olist-orders-${REGION}}"
export ORDER_SYNC_QUEUE

echo "order-sync: region=${REGION} queue=${ORDER_SYNC_QUEUE}"
python /app/worker.py
echo "order-sync: worker đã thoát"
