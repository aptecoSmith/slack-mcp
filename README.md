# Slack MCP Server

_An MCP-compliant server for Slack workspace integration using FastMCP and Python._

---

## Project Overview
This project implements a Model Context Protocol (MCP) server for Slack, enabling AI models to interact with Slack workspaces efficiently. It supports large data responses, chunking, and advanced Slack workspace management via a set of standardized tools.

## Required Environment Variables

To run the Slack MCP server, you must provide the following environment variables (via `.env` file or Docker `-e` flags):

- `SLACK_BOT_TOKEN` – Your Slack bot token (starts with `xoxb-`)

You can copy `.env.example` to `.env` and fill in your value:
```sh
cp .env.example .env
```

Alternatively, you can pass this variable directly when running Docker:
```sh
docker run --rm -it -e SLACK_BOT_TOKEN=... slack-mcp
```

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd slack_mcp
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set required environment variables:**
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
   - `SLACK_BOT_TOKEN`: Your Slack bot token (required for API access)

## Running Tests

To run the unit and integration tests:

1. **Activate the virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1  # PowerShell on Windows
   # or
   venv\Scripts\activate.bat     # Command Prompt on Windows
   ```
2. **Run all tests:**
   ```powershell
   pytest
   ```
3. **Run a specific test file:**
   ```powershell
   pytest -v tests/test_integration_real_slack.py -k test_get_channels
   ```

**Note:** Integration tests require a valid `SLACK_BOT_TOKEN` in your `.env` file. Some tests may be skipped if this is not set or if Slack API rate limits are hit.

5. **Run the MCP server:**
   ```bash
   python -m slack_mcp.main
   ```

## Project Structure
- `slack_mcp/main.py` – MCP server entrypoint and tool definitions
- `requirements.txt` – Python dependencies
- `PLANNING.md` – Project architecture, goals, and constraints
- `TASK.md` – Task tracking and progress
- `tests/` – Pytest-based unit tests (to be implemented)

## Features & Tools
The server exposes the following MCP tools for Slack:
- `send_message`: Send a message to a channel or user (supports threads and blocks)
- `get_channels`: List channels with pagination and filtering
- `get_users`: List users with pagination and locale info
- `read_channel_messages`: Retrieve messages or threads from a channel
- `search_messages`: Search workspace messages
- `create_channel`: Create new public or private channels
- `invite_to_channel`: Invite users to a channel
- `upload_file`: Upload and share files in channels
- `get_channel_info`: Get detailed info about a channel
- `update_message`: Edit previously sent messages
- `delete_message`: Remove messages
- `get_user_info`: Retrieve detailed user profiles

All tools are described with comprehensive parameters and robust error handling, including Slack API rate limiting.

## Rate Limiting & User Feedback

- The server uses a built-in SlackRateLimiter to track and respect Slack Web API rate limits.
- If a rate limit is hit (HTTP 429), the server:
  - Returns an error response with ETA (in seconds and timestamp) for when the next request will be allowed.
  - Example response:
    ```json
    {
      "error": "ratelimited",
      "retry_after": 30,
      "eta": "2025-04-27T20:30:00",
      "message": "Rate limit hit for chat_postMessage. Waiting 30 seconds. ETA: 2025-04-27T20:30:00."
    }
    ```
- This ensures users and clients are always informed about delays and can retry or queue requests accordingly.
- See `slack_mcp/rate_limiter.py` for implementation details.

## Running with Docker

You can run the Slack MCP server in a containerized environment using Docker.

1. **Build the Docker image:**
   ```sh
   docker build -t slack-mcp .
   ```
2. **Run the container with your Slack bot token:**
   ```sh
   docker run --rm -it -e SLACK_BOT_TOKEN=xoxb-your-slack-bot-token slack-mcp
   ```
   - The server will start and listen on stdio (default FastMCP behavior).

**Notes:**
- The `.dockerignore` file ensures local caches, `.env`, and dev files are not included in the image.
- For development, you can mount your code as a volume:
  ```sh
  docker run --rm -it -v $(pwd)/slack_mcp:/app/slack_mcp -e SLACK_BOT_TOKEN=xoxb-your-slack-bot-token slack-mcp
  ```

## Integrating with Windsurf

To use this MCP server with Windsurf, add an entry to your `mcp_config.json` like this:

```json
"slack_py": {
  "command": "docker",
  "args": [
    "run",
    "--rm",
    "-i",
    "-e", "SLACK_BOT_TOKEN=xoxb-your-slack-bot-token",
    "slack-mcp"
  ]
}
```

- Replace `xoxb-your-slack-bot-token` with your actual Slack bot token.
- This will start the container and connect it to Windsurf using stdio transport.

## Contributing
Contributions are welcome! Please:
- Follow PEP8 and project conventions
- Add or update tests for new features
- Update documentation as needed

## License
Specify your license here (e.g., MIT, Apache 2.0, etc.)

---
_This README is a template. Update it as your project evolves._
