#!/bin/bash
# Database Initialization Script
# Runs Alembic migrations and loads default data

set -e

echo "Starting database initialization..."

# Wait for database to be ready
echo "Waiting for database connection..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "Database is ready!"

# Run Alembic migrations
echo "Running database migrations..."
cd /app
alembic upgrade head

echo "Database migrations completed successfully!"

# Load default symbol mappings
echo "Loading default symbol mappings..."
python -c "
from shared.database.connection import get_db_session
from shared.services.load_default_mappings import load_default_mappings

db = get_db_session()
try:
    load_default_mappings(db)
    db.commit()
    print('Default symbol mappings loaded successfully!')
except Exception as e:
    print(f'Error loading default mappings: {e}')
    db.rollback()
finally:
    db.close()
"

echo "Database initialization completed!"
