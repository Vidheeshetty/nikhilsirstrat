#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start Jupyter lab in the background
echo "Starting Jupyter Lab in the background..."
nohup jupyter lab \
    --port=8888 \
    --no-browser \
    --ip=0.0.0.0 \
    --ServerApp.iopub_data_rate_limit=10000000 \
    --ServerApp.rate_limit_window=10.0 > jupyter.log 2>&1 &

PID=$!
echo $PID > jupyter.pid
echo "Jupyter Lab started. PID ${PID}"
echo "PID saved to jupyter.pid"
echo "Output is being redirected to jupyter.log"
echo "To view logs, run: tail -f jupyter.log"
echo "To stop the server, run: ./stop_jupyter.sh" 