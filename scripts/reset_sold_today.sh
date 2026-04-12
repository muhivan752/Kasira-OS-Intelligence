#!/bin/bash
# Reset sold_today to 0 for all products at midnight WIB
# Run via cron: 0 17 * * * /var/www/kasira/scripts/reset_sold_today.sh
# (17:00 UTC = 00:00 WIB)

docker exec kasira-db-1 psql -U kasira -d kasira_db -c "UPDATE products SET sold_today = 0 WHERE sold_today > 0;"
