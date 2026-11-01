#!/usr/bin/env bash
python3 -c 'from olist_shop.shipping import shipping_fee; assert shipping_fee(200, "SP") == 0'
