#!/bin/bash

if [ -f .server.pids ]; then
    echo "Stopping servers using .server.pids..."
    while read -r pid; do
        if ps -p "$pid" > /dev/null; then
            echo "Stopping process $pid..."
            # Kill the process and its children
            pkill -P "$pid"
            kill "$pid" 2>/dev/null
        fi
    done < .server.pids
    rm .server.pids
    echo "Processes in .server.pids handled."
fi

# Fallback/Safety Net: Kill any remaining specific processes
echo "Cleaning up any remaining service processes..."

# Kill saas-authz-service (node/tsx)
pkill -f "tsx watch src/server.ts"
pkill -f "node dist/server.js"

# Kill backend (uvicorn)
pkill -f "uvicorn main:app"

# Kill frontend (vite)
pkill -f "vite"

echo "All 3 servers stopped."
