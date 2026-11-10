#!/bin/sh
set -e
# --no-owner: dump was made as "sandaru"; works with any POSTGRES_USER.
pg_restore --no-owner --role="$POSTGRES_USER" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  /docker-entrypoint-initdb.d/finance_db.dump
