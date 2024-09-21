#!/bin/bash

# Start Redis in the background
redis-server --daemonize yes

# Function to watch the directory and populate Redis
watch_directory() {
    echo "Starting directory watcher for $WATCHED_DIRECTORY"
    inotifywait -m -r -e modify,create,delete --format '%w%f' "$WATCHED_DIRECTORY" | while read file; do
        # Get the relative path
        relative_path="${file#$WATCHED_DIRECTORY/}"
        # Handle file creation and modification
        if [ -f "$file" ]; then
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -n "$REDIS_DB" SADD "$REDIS_SET" "$relative_path"
            echo "Added $relative_path to Redis"
        else
            # Handle file deletion
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -n "$REDIS_DB" SREM "$REDIS_SET" "$relative_path"
            echo "Removed $relative_path from Redis"
        fi
    done
}

# Start the directory watcher in the background
watch_directory &

# Start upload script every UPLOAD_DELAY_SECONDS seconds
echo "Starting periodic upload script with delay $UPLOAD_DELAY_SECONDS seconds"
while true; do
    python /app/upload_files.py
    echo "waiting $UPLOAD_DELAY_SECONDS seconds until next upload..."
    sleep "$UPLOAD_DELAY_SECONDS"
done
