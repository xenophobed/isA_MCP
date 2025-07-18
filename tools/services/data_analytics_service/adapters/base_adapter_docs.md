# BaseAdapter Documentation

## Overview

The `BaseAdapter` class is an abstract base class that provides common functionality for all data adapters in the data analytics service. It implements the `IAdapter` interface and provides a foundation for creating specific adapter implementations.

## Class: BaseAdapter

### Location
`tools/services/data_analytics_service/adapters/base_adapter.py`

### Inheritance
- Inherits from: `IAdapter`, `ABC`
- Implemented by: All specific adapter classes (MySQL, PostgreSQL, etc.)

### Constructor

```python
def __init__(self, name: str, adapter_type: str)
```

**Parameters:**
- `name` (str): Unique name for the adapter instance
- `adapter_type` (str): Type of adapter (e.g., "mysql", "postgresql")

**Description:**
Initializes the base adapter with name, type, and default configuration. Sets up statistics tracking and health monitoring.

### Core Methods

#### `async initialize(self, config: Dict[str, Any]) -> bool`

**Purpose:** Initialize the adapter with provided configuration

**Parameters:**
- `config` (Dict[str, Any]): Configuration dictionary containing adapter-specific settings

**Returns:** 
- `bool`: True if initialization successful, False otherwise

**Process:**
1. Validates configuration using `_validate_config()`
2. Calls adapter-specific initialization via `_initialize_adapter()`
3. Sets `is_initialized` flag
4. Updates statistics

#### `async health_check(self) -> bool`

**Purpose:** Check if the adapter is healthy and operational

**Returns:**
- `bool`: True if adapter is healthy, False otherwise

**Process:**
1. Checks initialization status
2. Performs adapter-specific health check via `_perform_health_check()`
3. Updates health status and timestamp

#### `get_capabilities(self) -> Dict[str, Any]`

**Purpose:** Get comprehensive information about adapter capabilities

**Returns:**
- `Dict[str, Any]`: Dictionary containing:
  - Basic adapter info (name, type, status)
  - Health information
  - Statistics
  - Adapter-specific capabilities

#### `get_stats(self) -> Dict[str, Any]`

**Purpose:** Get adapter performance statistics

**Returns:**
- `Dict[str, Any]`: Dictionary containing:
  - `total_operations`: Total number of operations executed
  - `successful_operations`: Number of successful operations
  - `failed_operations`: Number of failed operations
  - `last_operation_time`: Timestamp of last operation
  - `average_response_time`: Average response time in seconds

### Statistics and Monitoring

#### `_update_stats(self, operation_time: float, success: bool)`

**Purpose:** Update adapter statistics after operation completion

**Parameters:**
- `operation_time` (float): Time taken for operation in seconds
- `success` (bool): Whether operation was successful

#### `async _execute_with_stats(self, operation_name: str, operation_func, *args, **kwargs)`

**Purpose:** Execute operation with automatic statistics tracking

**Parameters:**
- `operation_name` (str): Name of operation for logging
- `operation_func`: Async function to execute
- `*args, **kwargs`: Arguments to pass to operation function

**Returns:** Result from operation function

**Features:**
- Automatic timing measurement
- Exception handling
- Statistics updates
- Logging

### Utility Methods

#### `_ensure_initialized(self)`

**Purpose:** Ensure adapter is initialized before operations

**Raises:** `RuntimeError` if adapter is not initialized

#### `async _safe_close_connection(self)`

**Purpose:** Safely close connection with error handling

**Features:**
- Handles both `close()` and `disconnect()` methods
- Supports both sync and async connection objects
- Error logging without raising exceptions

### Abstract Methods (Must be Implemented by Subclasses)

#### `async _validate_config(self, config: Dict[str, Any]) -> bool`

**Purpose:** Validate adapter-specific configuration

**Parameters:**
- `config` (Dict[str, Any]): Configuration to validate

**Returns:** `bool` - True if configuration is valid

#### `async _initialize_adapter(self) -> None`

**Purpose:** Perform adapter-specific initialization

**Description:** Establish connections, validate credentials, setup resources

#### `async _perform_health_check(self) -> bool`

**Purpose:** Perform adapter-specific health check

**Returns:** `bool` - True if adapter is healthy

#### `_get_specific_capabilities(self) -> Dict[str, Any]`

**Purpose:** Get adapter-specific capabilities

**Returns:** `Dict[str, Any]` - Adapter-specific capability information

## Usage Example

```python
class MyAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("my_adapter", "custom")
    
    async def _validate_config(self, config):
        return "host" in config and "port" in config
    
    async def _initialize_adapter(self):
        # Setup connection, validate credentials, etc.
        pass
    
    async def _perform_health_check(self):
        # Check if connection is alive
        return True
    
    def _get_specific_capabilities(self):
        return {"supports_transactions": True}

# Usage
adapter = MyAdapter()
config = {"host": "localhost", "port": 5432}

if await adapter.initialize(config):
    print("Adapter ready!")
    
    # Check health
    if await adapter.health_check():
        print("Adapter is healthy")
    
    # Get capabilities
    caps = adapter.get_capabilities()
    print(f"Adapter capabilities: {caps}")
```

## Error Handling

The `BaseAdapter` includes comprehensive error handling:

- Configuration validation errors
- Initialization failures
- Health check failures
- Connection closing errors

All errors are logged appropriately and statistics are updated to reflect failure states.

## Thread Safety

The base adapter is designed to be thread-safe for statistics updates and health monitoring. However, specific adapter implementations should ensure thread safety for their connection management.

## Extension Points

When creating a new adapter:

1. Inherit from `BaseAdapter`
2. Implement all abstract methods
3. Call `super().__init__()` with appropriate name and type
4. Use `_execute_with_stats()` for operations that should be tracked
5. Use `_ensure_initialized()` before performing operations
6. Use `_safe_close_connection()` for cleanup