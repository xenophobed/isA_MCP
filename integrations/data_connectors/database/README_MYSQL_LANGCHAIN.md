# MySQL and LangChain Integration

This document provides a comprehensive guide to using MySQL with LangChain in this project. We've created several solutions to address different use cases and connection challenges.

## Table of Contents

1. [Direct MySQL Connection](#direct-mysql-connection)
2. [LangChain-Compatible Adapter](#langchain-compatible-adapter)
3. [Example Usage](#example-usage)
4. [Troubleshooting](#troubleshooting)

## Direct MySQL Connection

The `mysql_connection.py` file provides direct connection capabilities to MySQL using PyMySQL. This is the most reliable method for connecting to the database.

```python
from app.services.graph.mysql_connection import connect_to_mysql, MySQLDatabase

# Option 1: Using the connect_to_mysql function
db = connect_to_mysql()
result = db.run("SELECT * FROM classes LIMIT 5;")
print(result)

# Option 2: Using the MySQLDatabase class directly
db = MySQLDatabase(
    host="your_host",
    user="your_user",
    password="your_password",
    database="your_database",
    port=3306
)
result = db.run("SELECT * FROM classes LIMIT 5;")
print(result)

# Get available tables
tables = db.get_usable_table_names()
print(tables)

# Get table information
table_info = db.get_table_info("classes")
print(table_info)
```

## LangChain-Compatible Adapter

To use MySQL with LangChain's `SQLDatabaseToolkit`, we've created a custom adapter in `mysql_langchain_adapter.py` that extends LangChain's `SQLDatabase` class but uses direct PyMySQL connections for better stability.

```python
from app.services.graph.mysql_langchain_adapter import get_langchain_db
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI

# Get a LangChain-compatible database instance
db = get_langchain_db()

# Create a SQLDatabaseToolkit
toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))

# Get the tools
tools = toolkit.get_tools()

# Use the list_tables tool
list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
tables_result = list_tables_tool.invoke("")
print(f"Available tables: {tables_result}")

# Use the schema tool
get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
schema_result = get_schema_tool.invoke("classes")
print(f"Schema for classes table: {schema_result}")

# Use the query tool
query_tool = next(tool for tool in tools if tool.name == "sql_db_query")
query_result = query_tool.invoke("SELECT name FROM classes LIMIT 5;")
print(f"Query result: {query_result}")
```

### Creating an Agent

You can create a LangChain agent that uses the SQLDatabaseToolkit:

```python
from app.services.graph.mysql_langchain_adapter import get_langchain_db
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.agents.agent_types import AgentType

# Get a LangChain-compatible database instance
db = get_langchain_db()

# Create a SQLDatabaseToolkit
toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))

# Create an agent
agent = create_sql_agent(
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
    toolkit=toolkit,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    verbose=True
)

# Run the agent
result = agent.invoke({"input": "What are the names of the first 5 classes?"})
print(f"Agent result: {result}")
```

## Example Usage

We've provided several example files to demonstrate different ways to use MySQL with LangChain:

1. `app/services/graph/tests/mysql_example.py` - Basic direct connection example
2. `app/services/graph/tests/test_langchain_toolkit.py` - Testing the LangChain toolkit integration
3. `app/services/graph/tests/mysql_toolkit_example.py` - Comprehensive example of using the SQLDatabaseToolkit

### Direct Approach Example

If you encounter issues with the agent, you can use a direct approach:

```python
from app.services.graph.mysql_langchain_adapter import get_langchain_db
from langchain_openai import ChatOpenAI

# Get a LangChain-compatible database instance
db = get_langchain_db()

# Get the schema for the classes table
schema = db.get_table_info("classes")

# Run a query to get the class names
query = "SELECT name FROM classes LIMIT 5;"
result = db.run(query)

# Format the result for the LLM
formatted_result = f"Query: {query}\nResult: {result}"

# Create a prompt for the LLM
prompt = f"""
You are a helpful assistant that answers questions about a database.

Database schema:
{schema}

I ran the following query and got these results:
{formatted_result}

Based on this information, please answer the following question:
What are the names of the first 5 classes?
"""

# Get the answer from the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
answer = llm.invoke(prompt)
print(f"LLM answer: {answer.content}")
```

## Troubleshooting

### Common Issues

1. **Lost connection to MySQL server during query**
   - This is a common issue with certain MySQL servers, particularly regarding security settings or network configurations.
   - Our adapter handles this by falling back to direct PyMySQL connections.

2. **SQLAlchemy connection errors**
   - The adapter attempts to create a SQLAlchemy engine but falls back to a minimal engine-like object if that fails.
   - This ensures compatibility with LangChain's SQLDatabaseToolkit while maintaining stability.

3. **Agent not returning expected output**
   - If the agent doesn't return the expected output, try the direct approach shown above.
   - This bypasses the agent and directly uses the LLM with formatted database information.

### Debugging

If you encounter issues, you can enable more verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

You can also inspect the raw query results:

```python
from app.services.graph.mysql_langchain_adapter import get_langchain_db

db = get_langchain_db()
result = db.run("SELECT * FROM classes LIMIT 5;")
print(f"Raw result: {result}")

# Extract data from the result
data = eval(result)  # Convert string representation to Python object
for row in data:
    print(row)
```

## File Structure

- `app/services/graph/mysql_connection.py` - Core MySQL connection functionality
- `app/services/graph/mysql_langchain_adapter.py` - LangChain adapter for MySQL
- `app/services/graph/tests/mysql_example.py` - Basic direct connection example
- `app/services/graph/tests/test_langchain_toolkit.py` - Testing the LangChain toolkit integration
- `app/services/graph/tests/mysql_toolkit_example.py` - Comprehensive example of using the SQLDatabaseToolkit 