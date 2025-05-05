"""
Slack MCP Server entrypoint using FastMCP and stdio transport.
Implements Slack workspace tools as described in project planning and task.
"""
import os
from fastmcp.server import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Any, Dict, Optional, List
from .rate_limiter import SlackRateLimiter

rate_limiter = SlackRateLimiter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN environment variable is required.")

slack_client = WebClient(token=SLACK_BOT_TOKEN)

# --- FastMCP Server Setup ---
server = FastMCP(name="Slack MCP Server")

# --- Tool Implementations ---
@server.tool(
    name="send_message",
    description="Sends a message to a specified Slack channel or direct message. Can be used to post new messages or reply to threads. Supports both plain text and rich formatting with blocks."
)
def send_message(channel: str, text: str, thread_ts: Optional[str] = None, blocks: Optional[List[dict]] = None) -> Dict[str, Any]:
    """
    Sends a message to a specified Slack channel or direct message. Can be used to post new messages or reply to threads. Supports both plain text and rich formatting with blocks.
    """
    def slack_call():
        return slack_client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            blocks=blocks
        ).data
    result = rate_limiter.wrap("chat_postMessage", slack_call)
    return result

@server.tool(
    name="get_channels",
    description="Retrieves a list of channels from the Slack workspace. Supports pagination for handling large workspaces. Returns channel IDs, names, topics, purposes, and member counts."
)
def get_channels(types: Optional[str] = None, exclude_archived: bool = True, limit: Optional[int] = None, cursor: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves a list of channels from the Slack workspace. Supports pagination for handling large workspaces. Returns channel IDs, names, topics, purposes, and member counts.
    """
    def slack_call():
        params = {"exclude_archived": exclude_archived}
        if types:
            params["types"] = types
        if limit:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return slack_client.conversations_list(**params).data
    result = rate_limiter.wrap("conversations_list", slack_call)
    return result

@server.tool(
    name="get_users",
    description="Retrieves a list of users from the Slack workspace. Handles pagination automatically for workspaces with many users. Returns user IDs, names, real names, display names, emails (if available), and status."
)
def get_users(limit: Optional[int] = None, cursor: Optional[str] = None, include_locale: Optional[bool] = None) -> Dict[str, Any]:
    """
    Retrieves a list of users from the Slack workspace. Handles pagination automatically for workspaces with many users. Returns user IDs, names, real names, display names, emails (if available), and status.
    """
    def slack_call():
        params = {}
        if limit:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        if include_locale is not None:
            params["include_locale"] = include_locale
        return slack_client.users_list(**params).data
    result = rate_limiter.wrap("users_list", slack_call)
    return result

@server.tool(
    name="find_users_by_name",
    description="Finds all Slack users whose real_name, display_name, or username contains the given substring (case-insensitive). Returns a list of matching user dicts."
)
def find_users_by_name(substring: str) -> Dict[str, Any]:
    """
    Finds all Slack users whose real_name, display_name, or username contains the given substring (case-insensitive).

    Args:
        substring (str): Substring to search for in user names.

    Returns:
        Dict[str, Any]: {"ok": True, "matches": [user, ...]} on success, or {"error": ...} on failure.
    """
    users = []
    cursor = None
    while True:
        res = get_users(cursor=cursor)
        if res.get("error") == "ratelimited":
            return res  # propagate rate limit info
        if not res.get("ok"):
            return {"error": res.get("error", res)}
        users.extend(res.get("members", []))
        cursor = res.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    query = substring.lower()
    matches = [
        user for user in users
        if any(query in (user.get(field, "") or "").lower() for field in ("real_name", "display_name", "name"))
    ]
    return {"ok": True, "matches": matches}

@server.tool(
    name="read_channel_messages",
    description="Retrieves message history from a specified channel. Can retrieve entire channel history or specific threads. Supports time-based filtering and pagination for handling large message volumes."
)
def read_channel_messages(channel: str, limit: int = 100, oldest: Optional[str] = None, latest: Optional[str] = None, inclusive: Optional[bool] = None, thread_ts: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves message history from a specified channel. Can retrieve entire channel history or specific threads. Supports time-based filtering and pagination for handling large message volumes.
    """
    def slack_call():
        params = {"channel": channel, "limit": limit}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        if inclusive is not None:
            params["inclusive"] = inclusive
        if thread_ts:
            params["ts"] = thread_ts
            return slack_client.conversations_replies(**params).data
        else:
            return slack_client.conversations_history(**params).data
    result = rate_limiter.wrap("conversations_history", slack_call)
    return result

@server.tool(
    name="search_messages",
    description="Searches for messages across all accessible channels using Slack's search functionality. Returns matching messages with channel context and highlights. Supports pagination for large result sets."
)
def search_messages(query: str, sort: Optional[str] = None, sort_dir: Optional[str] = None, count: Optional[int] = None, page: Optional[int] = None) -> Dict[str, Any]:
    """
    Searches for messages across all accessible channels using Slack's search functionality. Returns matching messages with channel context and highlights. Supports pagination for large result sets.
    """
    def slack_call():
        params = {"query": query}
        if sort:
            params["sort"] = sort
        if sort_dir:
            params["sort_dir"] = sort_dir
        if count:
            params["count"] = count
        if page:
            params["page"] = page
        return slack_client.search_messages(**params).data
    result = rate_limiter.wrap("search_messages", slack_call)
    return result

@server.tool(
    name="create_channel",
    description="Creates a new channel in the Slack workspace. Channel names must be lowercase, without spaces or periods, and cannot be longer than 80 characters."
)
def create_channel(name: str, is_private: Optional[bool] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new channel in the Slack workspace. Channel names must be lowercase, without spaces or periods, and cannot be longer than 80 characters.
    """
    def slack_call():
        params = {"name": name}
        if is_private is not None:
            params["is_private"] = is_private
        if team_id:
            params["team_id"] = team_id
        return slack_client.conversations_create(**params).data
    result = rate_limiter.wrap("conversations_create", slack_call)
    return result

@server.tool(
    name="invite_to_channel",
    description="Invites multiple users to a channel. The users must be valid members of the workspace, and the channel must exist."
)
def invite_to_channel(channel: str, users: str) -> Dict[str, Any]:
    """
    Invites multiple users to a channel. The users must be valid members of the workspace, and the channel must exist.
    """
    def slack_call():
        return slack_client.conversations_invite(channel=channel, users=users).data
    result = rate_limiter.wrap("conversations_invite", slack_call)
    return result

@server.tool(
    name="upload_file",
    description="Uploads a file to one or more Slack channels. Supports text files, images, PDFs, and other file types. Can be attached to threads and include an initial comment."
)
def upload_file(channels: str, content: str, filename: str, filetype: Optional[str] = None, initial_comment: Optional[str] = None, thread_ts: Optional[str] = None) -> Dict[str, Any]:
    """
    Uploads a file to one or more Slack channels. Supports text files, images, PDFs, and other file types. Can be attached to threads and include an initial comment.
    """
    try:
        params = {
            "channels": channels,
            "content": content,
            "filename": filename
        }
        if filetype:
            params["filetype"] = filetype
        if initial_comment:
            params["initial_comment"] = initial_comment
        if thread_ts:
            params["thread_ts"] = thread_ts
        def slack_call():
            return slack_client.files_upload(**params).data
        result = rate_limiter.wrap("files_upload", slack_call)
        return result
    except SlackApiError as e:
        return {"error": str(e), "details": getattr(e, "response", None)}
    except Exception as e:
        return {"error": str(e)}

@server.tool(
    name="get_channel_info",
    description="Retrieves detailed information about a specific channel, including its name, topic, purpose, creation date, creator, and optionally the number of members."
)
def get_channel_info(channel: str, include_num_members: Optional[bool] = None) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific channel, including its name, topic, purpose, creation date, creator, and optionally the number of members.
    """
    try:
        params = {"channel": channel}
        if include_num_members is not None:
            params["include_num_members"] = include_num_members
        def slack_call():
            return slack_client.conversations_info(**params).data
        result = rate_limiter.wrap("conversations_info", slack_call)
        return result
    except SlackApiError as e:
        return {"error": str(e), "details": getattr(e, "response", None)}
    except Exception as e:
        return {"error": str(e)}

@server.tool(
    name="update_message",
    description="Updates the content of a previously sent message. Can only update messages that were sent by the same bot. Supports both text updates and block updates."
)
def update_message(channel: str, ts: str, text: str, blocks: Optional[List[dict]] = None) -> Dict[str, Any]:
    """
    Updates the content of a previously sent message. Can only update messages that were sent by the same bot. Supports both text updates and block updates.
    """
    try:
        params = {"channel": channel, "ts": ts, "text": text}
        if blocks:
            params["blocks"] = blocks
        def slack_call():
            return slack_client.chat_update(**params).data
        result = rate_limiter.wrap("chat_update", slack_call)
        return result
    except SlackApiError as e:
        return {"error": str(e), "details": getattr(e, "response", None)}
    except Exception as e:
        return {"error": str(e)}

@server.tool(
    name="delete_message",
    description="Permanently deletes a message from a channel. Can only delete messages that were sent by the same bot."
)
def delete_message(channel: str, ts: str) -> Dict[str, Any]:
    """
    Permanently deletes a message from a channel. Can only delete messages that were sent by the same bot.
    """
    def slack_call():
        return slack_client.chat_delete(channel=channel, ts=ts).data
    result = rate_limiter.wrap("chat_delete", slack_call)
    return result

@server.tool(
    name="get_user_info",
    description="Retrieves detailed profile information about a specific user, including their name, title, phone, email, status, and other profile fields."
)
def get_user_info(user: str) -> Dict[str, Any]:
    """
    Retrieves detailed profile information about a specific user, including their name, title, phone, email, status, and other profile fields.
    """
    def slack_call():
        return slack_client.users_profile_get(user=user).data
    result = rate_limiter.wrap("users_profile_get", slack_call)
    return result


# --- FastMCP stdio run entrypoint ---
if __name__ == "__main__":
    server.run()
