#!/usr/bin/env bash
# PostgreSQL local de desarrollo; no modifica una instancia externa.
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pg_bin="${PG_BIN:-/usr/lib/postgresql/17/bin}"
pg_data="$project_root/.local/pgdata"
pg_socket="$project_root/.local/pgsocket"
mkdir -p "$pg_socket"
chmod 700 "$project_root/.local" "$pg_socket"
if [[ ! -x "$pg_bin/initdb" ]]; then
  echo 'Instala PostgreSQL y define PG_BIN con su directorio bin (initdb, pg_ctl, psql).' >&2
  exit 1
fi
case "${1:-start}" in
  start)
    if [[ ! -f "$pg_data/PG_VERSION" ]]; then
      "$pg_bin/initdb" -D "$pg_data" --username=gestor_epp --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --locale=C.UTF-8
    fi
    if ! "$pg_bin/pg_ctl" -D "$pg_data" status >/dev/null 2>&1; then
      "$pg_bin/pg_ctl" -D "$pg_data" -l "$project_root/.local/postgresql.log" -o "-h '' -k '$pg_socket' -p 55432" -w start
    fi
    if [[ "$("$pg_bin/psql" -h "$pg_socket" -p 55432 -U gestor_epp -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='gestor_epp'")" != 1 ]]; then
      "$pg_bin/createdb" -h "$pg_socket" -p 55432 -U gestor_epp gestor_epp
    fi
    echo "PostgreSQL disponible por socket: $pg_socket (puerto 55432, usuario y base gestor_epp)."
    ;;
  stop) "$pg_bin/pg_ctl" -D "$pg_data" -m fast -w stop ;;
  *) echo 'Uso: bash scripts/dev-db.sh [start|stop]' >&2; exit 1 ;;
esac
