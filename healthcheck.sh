#!/bin/bash

# Check if Redis is running
redis_status=$(redis-cli ping)
if [ "$redis_status" != "PONG" ]; then
    echo "Redis is not running"
    exit 1
fi

# Check if the directory watcher is running
pgrep -f "watch_directory" > /dev/null
if [ $? -ne 0 ]; then
    echo "Directory watcher is not running"
    exit 1
fi

# All checks passed
echo "Container is healthy"
exit 0
