#!/bin/bash
set -e

# Support custom PUID/PGID to match host permissions
PUID=${PUID:-999}
PGID=${PGID:-999}

# Update appuser UID/GID if needed
if [ "$(id -u appuser)" != "$PUID" ] || [ "$(id -g appuser)" != "$PGID" ]; then
    echo "Updating appuser UID:GID to $PUID:$PGID"
    groupmod -o -g "$PGID" appuser
    usermod -o -u "$PUID" appuser
fi

# Ensure appuser owns the home directory to avoid permission issues
chown appuser:appuser /home/appuser

# Ensure directories exist
mkdir -p /app/config /app/library /app/saved_stories /app/logs

# Copy alembic.ini if missing
if [ ! -f "/app/config/alembic.ini" ]; then
    echo "Initializing alembic.ini..."
    if [ -f "/app/defaults/config/alembic.ini" ]; then
        cp /app/defaults/config/alembic.ini /app/config/alembic.ini
    else
        echo "Warning: /app/defaults/config/alembic.ini not found."
    fi
fi

# Copy config.json.example if missing
if [ ! -f "/app/config/config.json.example" ]; then
    echo "Initializing config.json.example..."
    if [ -f "/app/defaults/config/config.json.example" ]; then
        cp /app/defaults/config/config.json.example /app/config/config.json.example
    else
        echo "Warning: /app/defaults/config/config.json.example not found."
    fi
fi

# If config.json is missing, create it from example
if [ ! -f "/app/config/config.json" ]; then
    echo "Initializing config.json from example..."
    if [ -f "/app/config/config.json.example" ]; then
        cp /app/config/config.json.example /app/config/config.json
    else
        echo "Warning: Could not create config.json (example missing)."
    fi
fi

# Fix permissions (force ownership to match current appuser UID/GID)
echo "Fixing permissions..."
chown -R appuser:appuser /app/config /app/library /app/saved_stories /app/logs

# Fix permissions for database files in root if they exist (legacy location)
for db_file in /app/library.db /app/library.db-shm /app/library.db-wal; do
    if [ -f "$db_file" ]; then
        chown appuser:appuser "$db_file"
    fi
done

# Ensure /app directory itself is writable by appuser so SQLite can create WAL files if DB is in root
chown appuser:appuser /app
chmod u+w /app

exec gosu appuser "$@"
