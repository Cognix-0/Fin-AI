FROM postgres:16-alpine
# Scripts in initdb.d run once, only when the data volume is empty.
COPY finance_db.dump /docker-entrypoint-initdb.d/finance_db.dump
COPY restore.sh /docker-entrypoint-initdb.d/10-restore.sh
