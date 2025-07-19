# isA MCP Management Portal

A modern, responsive web interface for managing and monitoring your isA MCP (Model Context Protocol) server.

## Features

### Overview
- **Dashboard**: Real-time system overview with usage metrics and activity feed
- **Analytics**: Live monitoring of MCP operations and performance metrics

### MCP Core Management
- **Tools**: Browse, test, and manage MCP tools with filtering by category
- **Prompts**: Manage system and user prompts with categorized organization
- **Resources**: Monitor and inspect MCP resources (databases, files, APIs)
- **Playground**: Test tools and prompts in real-time with JSON argument input

### System Administration
- **Monitoring**: Real-time system health and performance metrics
- **Logs**: Live log streaming with filtering and export capabilities
- **Configuration**: Server settings and auto-discovery configuration

## Quick Start

1. Start your MCP server:
   ```bash
   python smart_mcp_server.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8081/
   ```

3. The portal will automatically connect to your MCP server and display:
   - Available tools, prompts, and resources
   - Real-time system metrics
   - Live activity feed

## API Endpoints

The portal communicates with these MCP server endpoints:

- `GET /tools` - List available MCP tools
- `GET /prompts` - List available MCP prompts  
- `GET /resources` - List available MCP resources
- `POST /call-tool` - Execute an MCP tool
- `GET /health` - Server health and status

## Portal Structure

```
static/
├── index.html          # Main portal interface
├── css/
│   └── styles.css     # Modern styling with dark/light theme support
├── js/
│   └── app.js         # Portal JavaScript application
└── README.md          # This documentation
```

## Features in Detail

### Dashboard
- System statistics (tools, prompts, resources count)
- Usage charts for the last 7 days
- Recent activity feed
- Performance metrics table

### Tools Management
- Filter tools by category (web, data, analytics, memory, utility)
- View tool schemas and documentation
- Test tools directly in the interface
- Monitor tool performance and usage

### Playground
- Interactive tool testing environment
- JSON argument editor with syntax highlighting
- Real-time execution and result display
- Copy results to clipboard

### Logs
- Real-time log streaming
- Filter by log level, component, and time range
- Search functionality
- Export logs in JSON format
- Live connection status indicator

### Monitoring
- System health cards
- Real-time performance charts
- Resource usage monitoring
- Service status indicators

## Customization

The portal uses CSS custom properties for easy theming:

```css
:root {
    --primary: #2563eb;        /* Primary brand color */
    --background: #fafafa;     /* Background color */
    --foreground: #171717;     /* Text color */
    /* ... more variables */
}
```

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Modern JavaScript features are used, so older browsers may not be supported.

## Development

The portal is built with:
- Vanilla JavaScript (ES6+)
- Modern CSS with custom properties
- Chart.js for visualizations
- Lucide icons
- Inter font family

No build process is required - all files are served statically.