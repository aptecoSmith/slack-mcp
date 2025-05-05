# Using the Slack MCP Server in Another Project

This guide explains how to use the Slack MCP server from another project when it's running in a Docker container.

## Overview

The Slack MCP server provides a Model Context Protocol (MCP) interface to Slack's API, handling large responses through pagination and chunking. It's designed to be run as a Docker container and communicates via stdio (standard input/output).

## Setup Instructions

### 1. Build the Docker Image

First, build the Docker image for the Slack MCP server:

```bash
# From the slack_mcp project directory
docker build -t slack-mcp:latest .
```

### 2. Configure Your Client Project

Place the provided `mcp_client_config.json` file in your client project. This file contains all the configuration needed to connect to the Slack MCP server.

### 3. Environment Variables

Ensure you have the necessary environment variables set in your client project:

- `SLACK_BOT_TOKEN` (required): Your Slack Bot User OAuth Token
- `SUPABASE_URL` (optional): URL for Supabase if you're using it for data storage
- `SUPABASE_SERVICE_ROLE_KEY` (optional): Service role key for Supabase

### 4. Connecting to the MCP Server

#### Using a Python MCP Client

```python
import os
import json
from model_context_protocol import MCPClient

# Load the MCP configuration
with open("path/to/mcp_client_config.json", "r") as f:
    mcp_config = json.load(f)

# Initialize the MCP client
client = MCPClient(mcp_config)

# Example: Send a message to a Slack channel
response = client.invoke("send_message", {
    "channel": "C0123456789",  # Channel ID
    "text": "Hello from MCP client!"
})

print(response)
```

#### Using Other MCP Clients

The configuration file is compatible with any MCP client that supports the stdio transport. The client will use Docker to run the MCP server container and communicate with it via stdio.

## Available Tools

The MCP server provides the following tools for interacting with Slack:

1. `send_message` - Send messages to channels, direct messages, or threads
2. `get_channels` - List channels with pagination support
3. `get_users` - List users with pagination support
4. `find_users_by_name` - Search for users by name
5. `read_channel_messages` - Get message history from channels
6. `search_messages` - Search for messages across channels
7. `create_channel` - Create new channels
8. `invite_to_channel` - Invite users to channels
9. `upload_file` - Upload files to channels
10. `get_channel_info` - Get detailed channel information
11. `update_message` - Update existing messages
12. `delete_message` - Delete messages
13. `get_user_info` - Get detailed user information

Each tool has parameters defined in the configuration file.

## Sending Direct Messages

To send a direct message to a user using the MCP server, you can use the `send_message` tool in two ways:

### Using the User ID directly

```python
response = client.invoke("send_message", {
    "channel": "U0123456789",  # User ID for direct messaging
    "text": "Hello, this is a direct message!"
})
```

### Using the IM (Direct Message) channel ID

```python
# First, find the IM channel for a specific user
channels = client.invoke("get_channels", {
    "types": "im"  # Get only direct message channels
})

# Find the channel for the specific user
for channel in channels.get("channels", []):
    if channel.get("user") == "U0123456789":  # The user ID you want to message
        dm_channel_id = channel["id"]  # This will be a D-prefixed ID
        break

# Then send the message to that channel
response = client.invoke("send_message", {
    "channel": dm_channel_id,
    "text": "Hello, this is a direct message!"
})
```

### Finding Users by Name

```python
# Find a user by name
users_result = client.invoke("find_users_by_name", {
    "substring": "John Doe"  # The name to search for
})

# If found, get their user ID and send a message
if users_result.get("matches"):
    user_id = users_result["matches"][0]["id"]
    
    # Send direct message
    response = client.invoke("send_message", {
        "channel": user_id,
        "text": "Hello, I found you by name!"
    })
```

## Reading Messages from Channels

To read messages from a channel or direct message conversation, use the `read_channel_messages` tool:

```python
# Read the most recent messages from a channel
response = client.invoke("read_channel_messages", {
    "channel": "C0123456789",  # Channel ID
    "limit": 100  # Number of messages to retrieve (default: 100)
})

# Print the messages
for message in response.get("messages", []):
    print(f"{message.get('user')}: {message.get('text')}")
```

### Reading Thread Replies

```python
# Read replies in a thread
response = client.invoke("read_channel_messages", {
    "channel": "C0123456789",  # Channel ID
    "thread_ts": "1234567890.123456",  # Timestamp of the parent message
    "limit": 50  # Number of replies to retrieve
})

# Print the thread replies
for reply in response.get("messages", []):
    print(f"{reply.get('user')}: {reply.get('text')}")
```

### Time-Based Filtering

```python
# Read messages from a specific time range
response = client.invoke("read_channel_messages", {
    "channel": "C0123456789",
    "oldest": "1609459200.000000",  # Unix timestamp (e.g., Jan 1, 2021)
    "latest": "1612137600.000000",  # Unix timestamp (e.g., Feb 1, 2021)
    "inclusive": True  # Include messages at the exact timestamps
})
```

### Reading Direct Message History

```python
# Get direct message history with a user
response = client.invoke("read_channel_messages", {
    "channel": "D0123456789",  # DM channel ID (starts with D)
    "limit": 50
})
```

## Pagination Handling

For methods that return large datasets (like `get_users` or `get_channels`), the server handles pagination automatically. You can use the `cursor` parameter to navigate through pages of results.

Example:

```python
# Get first page of users
response = client.invoke("get_users", {"limit": 100})

# Get next page using the cursor from the previous response
if response.get("response_metadata", {}).get("next_cursor"):
    next_cursor = response["response_metadata"]["next_cursor"]
    next_page = client.invoke("get_users", {
        "limit": 100,
        "cursor": next_cursor
    })
```

## Error Handling

The MCP server returns error information in a standardized format:

```json
{
  "error": "Error message",
  "details": { ... }
}
```

Check for the presence of an "error" key in the response to handle errors appropriately.

## Troubleshooting

1. **Connection Issues**: Ensure Docker is running and the image is built correctly
2. **Authentication Errors**: Verify your SLACK_BOT_TOKEN is valid and has the necessary scopes
3. **Rate Limiting**: The server includes rate limiting, but you may still encounter Slack API rate limits

For more detailed information, refer to the main project documentation.
