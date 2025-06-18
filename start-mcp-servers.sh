#!/bin/bash
# start-mcp-servers.sh

# Create systemd service files
for port in 8001 8002 8003; do
    cat > /etc/systemd/system/mcp-server-${port}.service << EOF
[Unit]
Description=MCP Server on Port ${port}
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/opt/mcp-server
ExecStart=/opt/mcp-server/venv/bin/python server.py --port ${port}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl enable mcp-server-${port}
    systemctl start mcp-server-${port}
done

echo "All MCP servers started on ports 8001, 8002, 8003"