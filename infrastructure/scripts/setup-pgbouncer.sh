#!/bin/bash
# PgBouncer Setup Script
# Configures PgBouncer for connection pooling

set -e

echo "Setting up PgBouncer configuration..."

# Create PgBouncer configuration directory
mkdir -p /etc/pgbouncer

# Generate pgbouncer.ini
cat > /etc/pgbouncer/pgbouncer.ini <<EOF
[databases]
trading_platform = host=${DB_HOST} port=5432 dbname=${DB_NAME}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
reserve_pool_size = 5
reserve_pool_timeout = 3
max_db_connections = 100
server_idle_timeout = 600
server_lifetime = 3600
server_reset_query = DISCARD ALL
ignore_startup_parameters = extra_float_digits
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
EOF

# Generate userlist.txt with MD5 password
echo "Generating user credentials..."
python3 -c "
import hashlib
username = '${DB_USER}'
password = '${DB_PASSWORD}'
md5_hash = 'md5' + hashlib.md5((password + username).encode()).hexdigest()
print(f'\"{username}\" \"{md5_hash}\"')
" > /etc/pgbouncer/userlist.txt

chmod 600 /etc/pgbouncer/userlist.txt

echo "PgBouncer configuration completed!"
echo "Connection string: postgresql://${DB_USER}:${DB_PASSWORD}@localhost:6432/${DB_NAME}"
