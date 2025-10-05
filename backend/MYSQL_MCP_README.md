# MySQL MCP Server Integration

This document describes the MySQL Model Context Protocol (MCP) server integration for the multi-org chatbot system. The MySQL MCP server provides a centralized database interface that other MCPs (like Docling and Graph) can use to perform SQL operations.

## Overview

The MySQL MCP server acts as a central database gateway that:
- Provides REST endpoints for SQL operations
- Handles tabular data operations (SELECT, INSERT, UPDATE)
- Offers schema introspection capabilities
- Integrates with the existing RAG system
- Enables other MCPs to query the database through a standardized interface

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Docling MCP   │    │   Graph MCP     │    │  Other MCPs     │
│   (Port 5000)   │    │   (Port 5001)   │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      MySQL MCP Server     │
                    │       (Port 5002)         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      MySQL Database       │
                    │    (chatbot_rag)          │
                    └───────────────────────────┘
```

## REST Endpoints

### 1. Query Endpoint
**POST** `/query`

Execute SELECT and JOIN SQL queries with optional parameters.

**Request Body:**
```json
{
  "query": "SELECT * FROM users WHERE domain_id = :domain_id",
  "parameters": {
    "domain_id": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "domain_id": 1
    }
  ],
  "columns": ["id", "username", "email", "domain_id"],
  "row_count": 1,
  "message": "Query executed successfully, returned 1 rows"
}
```

### 2. Insert Endpoint
**POST** `/insert`

Insert new rows into a table.

**Request Body:**
```json
{
  "table": "feedback",
  "data": {
    "user_id": 1,
    "domain_id": 1,
    "content": "Great service!",
    "rating": 5,
    "question": "How was your experience?"
  }
}
```

**Response:**
```json
{
  "success": true,
  "last_insert_id": 123,
  "affected_rows": 1,
  "message": "Successfully inserted 1 row(s)"
}
```

### 3. Update Endpoint
**POST** `/update`

Update existing rows in a table.

**Request Body:**
```json
{
  "table": "users",
  "data": {
    "role_based": "admin"
  },
  "where_clause": "id = :user_id",
  "where_parameters": {
    "user_id": 1
  }
}
```

**Response:**
```json
{
  "success": true,
  "affected_rows": 1,
  "message": "Successfully updated 1 row(s)"
}
```

### 4. Schema Endpoints

#### Get All Tables
**GET** `/schema`

Returns schema information for all tables.

#### Get Specific Table
**GET** `/schema/{table_name}`

Returns detailed schema information for a specific table.

**Response:**
```json
{
  "success": true,
  "table_name": "users",
  "columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "nullable": false,
      "primary_key": true,
      "autoincrement": true
    }
  ],
  "indexes": [...],
  "foreign_keys": [...]
}
```

### 5. Health Check
**GET** `/health`

Check server and database connectivity.

## MCP Tools

The MySQL MCP server also provides MCP tools that can be used by other MCP clients:

- `query_mysql_tool`: Execute SELECT queries
- `insert_mysql_tool`: Insert new records
- `update_mysql_tool`: Update existing records
- `get_mysql_schema_tool`: Get schema information
- `get_table_stats_tool`: Get table statistics

## Integration Examples

### Docling Integration

```python
from app.MCP.mysql_mcp_client import DoclingMySQLIntegration

# Store processed chunks from Docling
docling_integration = DoclingMySQLIntegration()
chunks = [{"content": "Sample text", "metadata": {"page": 1}}]
result = docling_integration.store_processed_chunks(doc_id=1, chunks=chunks)
```

### Graph Integration

```python
from app.MCP.mysql_mcp_client import GraphMySQLIntegration

# Get chunks for graph building
graph_integration = GraphMySQLIntegration()
chunks = graph_integration.get_chunks_for_graph_building(domain_id=1)
```

### Direct Client Usage

```python
from app.MCP.mysql_mcp_client import MySQLMCPClient

client = MySQLMCPClient()

# Query users by domain
users = client.query(
    "SELECT * FROM users WHERE domain_id = :domain_id",
    {"domain_id": 1}
)

# Insert new feedback
result = client.insert("feedback", {
    "user_id": 1,
    "domain_id": 1,
    "content": "Great!",
    "rating": 5,
    "question": "How was it?"
})
```

## Helper Functions

The MySQL MCP client provides several helper functions for common operations:

- `get_users_by_domain(domain_id)`: Get all users for a domain
- `get_chunks_for_document(doc_id)`: Get all chunks for a document
- `get_chat_history_for_user(user_id, limit)`: Get user's chat history
- `get_domain_statistics(domain_id)`: Get comprehensive domain stats
- `insert_feedback(...)`: Insert feedback record
- `update_user_role(user_id, new_role)`: Update user role

## Security Features

1. **Query Restrictions**: Only SELECT, SHOW, DESCRIBE, and EXPLAIN queries are allowed through the query endpoint
2. **Parameterized Queries**: Support for parameterized queries to prevent SQL injection
3. **Required WHERE Clauses**: UPDATE operations require WHERE clauses for safety
4. **Transaction Management**: Proper transaction handling with rollback on errors

## Database Schema

The MySQL MCP server works with the existing database schema:

- `domains`: Organization domains
- `users`: User accounts
- `docs`: Documents
- `chunks`: Document chunks for RAG
- `feedback`: User feedback
- `chat_sessions`: Chat sessions
- `chat_messages`: Chat messages
- `chat_sources`: Message sources

## Starting the MySQL MCP Server

### Option 1: Start All MCP Servers
```bash
cd backend
python start_mcp_servers.py
```

This will start:
- Docling MCP on port 5000
- Graph MCP on port 5001
- MySQL MCP on port 5002

### Option 2: Start MySQL MCP Only
```bash
cd backend
python -m uvicorn app.MCP.mysql_mcp_server:fastapi_app --host 127.0.0.1 --port 5002 --reload
```

## Testing

Run the integration test suite:

```bash
cd backend
python test_mysql_mcp_integration.py
```

This will test:
- Server connectivity
- All REST endpoints
- Helper functions
- MCP integrations
- Complex queries and JOINs

## Configuration

The MySQL MCP server uses the same database configuration as the main application:

- Database URL from `DATABASE_URL` environment variable
- Default: `mysql+pymysql://root:12345678@127.0.0.1:3306/chatbot_rag`
- Connection pooling and pre-ping enabled

## Error Handling

The server provides comprehensive error handling:

- Database connection errors
- SQL syntax errors
- Parameter validation errors
- Transaction rollback on failures
- Detailed error messages in responses

## Performance Considerations

- Connection pooling for better performance
- Parameterized queries for security and performance
- Efficient schema introspection
- Proper transaction management

## Future Enhancements

Potential improvements for the MySQL MCP server:

1. **Caching**: Add Redis caching for frequently accessed data
2. **Rate Limiting**: Implement rate limiting for API endpoints
3. **Audit Logging**: Add audit trails for database operations
4. **Batch Operations**: Support for batch inserts and updates
5. **Advanced Queries**: Support for more complex query types
6. **Metrics**: Add performance metrics and monitoring

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure MySQL MCP server is running on port 5002
2. **Database Connection Failed**: Check database credentials and connectivity
3. **Permission Denied**: Verify database user has appropriate permissions
4. **Query Timeout**: Check for long-running queries and optimize

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://127.0.0.1:5002/docs
- **ReDoc**: http://127.0.0.1:5002/redoc

This provides interactive API documentation for all endpoints.
