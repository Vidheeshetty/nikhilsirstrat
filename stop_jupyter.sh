#!/bin/bash

PID_FILE="jupyter.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping Jupyter Lab process with PID: $PID"
    kill "$PID"
    sleep 2 # Give it a moment to shut down

    # Check if the process is still running
    if ps -p "$PID" > /dev/null; then
        echo "Process $PID did not stop gracefully. Forcing kill..."
        kill -9 "$PID"
    else
        echo "Jupyter Lab stopped successfully."
    fi

    rm "$PID_FILE"
    # Optionally, remove the log file as well
    if [ -f "jupyter.log" ]; then
        rm "jupyter.log"
        echo "Removed jupyter.log"
    fi
else
    echo "Jupyter Lab PID file not found. Is the server running?"
fi 