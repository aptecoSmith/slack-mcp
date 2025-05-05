"""
Integration test for Slack MCP Server using the real Slack API.
Requires a valid SLACK_BOT_TOKEN in a .env file in the project root.

This test will check if a user named 'John Smith' exists in the Slack workspace.
"""
import os
from dotenv import load_dotenv
load_dotenv()  # Ensure .env is loaded before importing main
from slack_mcp import main
import pytest

# Load environment variables from .env
load_dotenv()

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN"),
    reason="SLACK_BOT_TOKEN not set in environment/.env file."
)
def test_find_john_smith():
    """
    Test that the user 'John Smith' exists in the Slack workspace.
    """
    users = []
    cursor = None
    # Paginate through all users
    while True:
        res = main.get_users(cursor=cursor)
        if res.get("error") and "ratelimited" in res["error"]:
            pytest.skip("Slack API rate limit reached; try again later.")
        assert res.get("ok"), f"Slack API error: {res.get('error', res)}"
        users.extend(res["members"])
        cursor = res.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    johns = [u for u in users if u.get("real_name", "").lower() == "john smith"]
    assert johns, "User 'John Smith' not found in Slack workspace."
    # Optionally print the user(s) found
    for user in johns:
        print(f"Found: {user['id']} - {user.get('real_name')} ({user.get('name')})")

def test_find_joe():
    """
    Test that at least one user with 'Joe' in their name exists in the Slack workspace.
    """
    res = main.find_users_by_name("Joe")
    if res.get("error") and "ratelimited" in res["error"]:
        pytest.skip("Slack API rate limit reached; try again later.")
    assert res.get("ok"), f"Slack API error: {res.get('error', res)}"
    matches = res.get("matches", [])
    assert matches, "No user with 'Joe' in their name found in Slack workspace."
    print(f"Found {len(matches)} user(s) with 'Joe' in their name:")
    for user in matches:
        print(f"Found: {user['id']} - {user.get('real_name')} ({user.get('name')})")

def test_send_message_to_john_smith():
    """
    Find John Smith and send a test message to him. Skip if not found or on rate limit.
    """
    # Find John Smith's user ID
    res = main.find_users_by_name("John Smith")
    if res.get("error") and "ratelimited" in res["error"]:
        pytest.skip("Slack API rate limit reached; try again later.")
    assert res.get("ok"), f"Slack API error: {res.get('error', res)}"
    johns = [u for u in res.get("matches", []) if u.get("real_name", "").lower() == "john smith"]
    if not johns:
        pytest.skip("User 'John Smith' not found in Slack workspace.")
    user_id = johns[0]["id"]
    # Send a test message via direct message
    send_res = main.send_message(channel=user_id, text="Hello from automated test!")
    if send_res.get("error") and "ratelimited" in send_res["error"]:
        pytest.skip("Slack API rate limit reached; try again later.")
    print(f"send_message result: {send_res}")
    assert send_res.get("ok"), f"Failed to send message: {send_res.get('error', send_res)}"

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN"),
    reason="SLACK_BOT_TOKEN not set in environment/.env file."
)
def test_get_channels():
    """
    Test that get_channels returns a list of channels and prints the number found.
    """
    cursor = None
    all_channels = []
    while True:
        res = main.get_channels(cursor=cursor)
        if res.get("error") and "ratelimited" in res["error"]:
            pytest.skip("Slack API rate limit reached; try again later.")
        assert res.get("ok"), f"Slack API error: {res.get('error', res)}"
        channels = res.get("channels", [])
        all_channels.extend(channels)
        cursor = res.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    print(f"Found {len(all_channels)} channel(s) in the Slack workspace.")
    for channel in all_channels:
        print(f"Channel: {channel.get('id')} - {channel.get('name')}")
    assert all_channels, "No channels found in Slack workspace."

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN"),
    reason="SLACK_BOT_TOKEN not set in environment/.env file."
)
def test_last_message_from_general_channel():
    """
    Test that reads the last message from the general channel and verifies
    if it was sent by one of the listed users.
    
    This test will:
    1. Find the general channel ID
    2. Get the latest message from that channel
    3. Get a list of users
    4. Check if the message sender is in the users list
    5. Log the message content, sender, and verification result
    """
    # List of user names to check against (can be real_name or display_name)
    target_users = ["John Smith", "Joe", "Admin"]
    
    # Step 1: Find the general channel
    channels_res = main.get_channels()
    if channels_res.get("error") and "ratelimited" in channels_res["error"]:
        pytest.skip("Slack API rate limit reached; try again later.")
    assert channels_res.get("ok"), f"Slack API error: {channels_res.get('error', channels_res)}"
    
    general_channel = None
    for channel in channels_res.get("channels", []):
        if channel.get("name") == "general":
            general_channel = channel
            break
    
    assert general_channel, "General channel not found in Slack workspace."
    general_channel_id = general_channel["id"]
    print(f"Found general channel with ID: {general_channel_id}")
    
    # Step 2: First try to join the channel to ensure we have access
    try:
        print(f"Attempting to join the general channel...")
        join_res = main.slack_client.conversations_join(channel=general_channel_id)
        if join_res["ok"]:
            print(f"Successfully joined the general channel or already a member")
        else:
            print(f"Could not join the general channel: {join_res.get('error')}")
    except Exception as e:
        print(f"Error joining the general channel: {str(e)}")
        if "already_in_channel" not in str(e):
            pytest.skip(f"Cannot access the general channel: {str(e)}")
        else:
            print("Bot is already in the channel")
    
    # Now try to get messages
    messages_res = main.read_channel_messages(channel=general_channel_id, limit=1)
    
    if messages_res.get("error") and "ratelimited" in messages_res["error"]:
        pytest.skip("Slack API rate limit reached; try again later.")
    assert messages_res.get("ok"), f"Slack API error: {messages_res.get('error', messages_res)}"
    
    messages = messages_res.get("messages", [])
    assert messages, "No messages found in the general channel."
    
    last_message = messages[0]
    sender_id = last_message.get("user")
    message_text = last_message.get("text")
    message_ts = last_message.get("ts")
    
    print(f"Last message in general channel:")
    print(f"  Time: {message_ts}")
    print(f"  Sender ID: {sender_id}")
    print(f"  Text: {message_text}")
    
    # Step 3: Get user information
    users = []
    cursor = None
    while True:
        users_res = main.get_users(cursor=cursor)
        if users_res.get("error") and "ratelimited" in users_res["error"]:
            pytest.skip("Slack API rate limit reached; try again later.")
        assert users_res.get("ok"), f"Slack API error: {users_res.get('error', users_res)}"
        users.extend(users_res["members"])
        cursor = users_res.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    
    # Step 4: Find the sender in the users list
    sender = None
    for user in users:
        if user["id"] == sender_id:
            sender = user
            break
    
    assert sender, f"Sender with ID {sender_id} not found in users list."
    
    sender_name = sender.get("real_name") or sender.get("name")
    print(f"Message sent by: {sender_name} ({sender_id})")
    
    # Step 5: Check if the sender is in the complete list of workspace users
    found_in_users_list = any(user["id"] == sender_id for user in users)
    
    print(f"Is sender found in the complete workspace users list? {'Yes' if found_in_users_list else 'No'}")
    print(f"Total users in workspace: {len(users)}")
    
    # This should always be true if we found the sender earlier
    assert found_in_users_list, f"Sender {sender_name} ({sender_id}) not found in the complete workspace users list"
    
    # Optional: Also check against our target users list for informational purposes
    is_target_user = any(
        target_user.lower() in (sender.get("real_name", "").lower() or 
                              sender.get("name", "").lower() or 
                              sender.get("display_name", "").lower())
        for target_user in target_users
    )
    
    print(f"Is sender in target users list? {'Yes' if is_target_user else 'No'}")
    print(f"Target users: {', '.join(target_users)}")
    
