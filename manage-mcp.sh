#!/bin/bash
# manage-mcp.sh

PORTS=(8001 8002 8003)
SCRIPT_DIR="/opt/mcp-server"

start_servers() {
    for port in "${PORTS[@]}"; do
        echo "Starting MCP server on port $port..."
        nohup python3 "$SCRIPT_DIR/server.py" --port $port > "$SCRIPT_DIR/logs/server-$port.log" 2>&1 &
        echo $! > "$SCRIPT_DIR/pids/server-$port.pid"
    done
}

stop_servers() {
    for port in "${PORTS[@]}"; do
        if [ -f "$SCRIPT_DIR/pids/server-$port.pid" ]; then
            pid=$(cat "$SCRIPT_DIR/pids/server-$port.pid")
            kill $pid 2>/dev/null
            rm "$SCRIPT_DIR/pids/server-$port.pid"
            echo "Stopped server on port $port"
        fi
    done
}

case "$1" in
    start)
        start_servers
        ;;
    stop)
        stop_servers
        ;;
    restart)
        stop_servers
        sleep 2
        start_servers
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac