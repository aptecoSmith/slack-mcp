"""
Unit tests for Slack MCP Server tools using pytest.
Covers expected use, edge, and failure cases for each tool.
"""
import os
import pytest
from slack_mcp import main

# Set up environment for testing (mock tokens)
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"

@pytest.fixture(autouse=True)
def patch_slack_client(monkeypatch):
    class DummyResponse:
        def __init__(self, data):
            self.data = data
    class DummyClient:
        def chat_postMessage(self, **kwargs):
            return DummyResponse({"ok": True, "channel": kwargs["channel"], "text": kwargs["text"]})
        def conversations_list(self, **kwargs):
            return DummyResponse({"ok": True, "channels": [{"id": "C1", "name": "general"}]})
        def users_list(self, **kwargs):
            return DummyResponse({"ok": True, "members": [{"id": "U1", "name": "alice"}]})
        def conversations_history(self, **kwargs):
            return DummyResponse({"ok": True, "messages": [{"text": "hi"}]})
        def conversations_replies(self, **kwargs):
            return DummyResponse({"ok": True, "messages": [{"text": "reply"}]})
        def search_messages(self, **kwargs):
            return DummyResponse({"ok": True, "messages": {"matches": [{"text": "search result"}]}})
        def conversations_create(self, **kwargs):
            return DummyResponse({"ok": True, "channel": {"id": "C2", "name": kwargs["name"]}})
        def conversations_invite(self, **kwargs):
            return DummyResponse({"ok": True, "channel": kwargs["channel"], "users": kwargs["users"]})
        def files_upload(self, **kwargs):
            return DummyResponse({"ok": True, "file": {"name": kwargs["filename"]}})
        def conversations_info(self, **kwargs):
            return DummyResponse({"ok": True, "channel": {"id": kwargs["channel"], "name": "general"}})
        def chat_update(self, **kwargs):
            return DummyResponse({"ok": True, "ts": kwargs["ts"], "text": kwargs["text"]})
        def chat_delete(self, **kwargs):
            return DummyResponse({"ok": True, "ts": kwargs["ts"]})
        def users_profile_get(self, **kwargs):
            return DummyResponse({"ok": True, "profile": {"real_name": "Alice"}})
    monkeypatch.setattr(main, "slack_client", DummyClient())

# --- send_message ---
def test_send_message_expected():
    res = main.send_message(channel="C1", text="Hello!")
    assert res["ok"] and res["channel"] == "C1" and res["text"] == "Hello!"

def test_send_message_edge():
    res = main.send_message(channel="C1", text="", thread_ts="123.456")
    assert res["ok"] and res["text"] == ""

def test_send_message_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "chat_postMessage", fail)
    res = main.send_message(channel="C1", text="fail")
    assert "error" in res

# --- get_channels ---
def test_get_channels_expected():
    res = main.get_channels()
    assert res["ok"] and isinstance(res["channels"], list)

def test_get_channels_edge():
    res = main.get_channels(types="im,mpim", limit=1)
    assert res["ok"]

def test_get_channels_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "conversations_list", fail)
    res = main.get_channels()
    assert "error" in res

# --- get_users ---
def test_get_users_expected():
    res = main.get_users()
    assert res["ok"] and isinstance(res["members"], list)

def test_get_users_edge():
    res = main.get_users(limit=1, include_locale=True)
    assert res["ok"]

def test_get_users_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "users_list", fail)
    res = main.get_users()
    assert "error" in res

# --- find_users_by_name ---
def test_find_users_by_name_expected():
    # Should match 'Joe Bloggs' and 'joey'
    def dummy_users(*a, **k):
        return {"ok": True, "members": [
            {"id": "U1", "real_name": "Joe Bloggs", "display_name": "joeb", "name": "joebloggs"},
            {"id": "U2", "real_name": "Alice Smith", "display_name": "alice", "name": "alicesmith"},
            {"id": "U3", "real_name": "Joey Tribbiani", "display_name": "joey", "name": "joeytrib"},
            {"id": "U4", "real_name": "Bob", "display_name": "bobby", "name": "bob"}
        ]}
    main.get_users = dummy_users
    res = main.find_users_by_name("joe")
    assert res["ok"] and len(res["matches"]) == 2
    ids = {u["id"] for u in res["matches"]}
    assert "U1" in ids and "U3" in ids

def test_find_users_by_name_case_insensitive():
    def dummy_users(*a, **k):
        return {"ok": True, "members": [
            {"id": "U1", "real_name": "Joe Bloggs", "display_name": "joeb", "name": "joebloggs"},
            {"id": "U2", "real_name": "JOE SMITH", "display_name": "joes", "name": "joesmith"}
        ]}
    main.get_users = dummy_users
    res = main.find_users_by_name("joe")
    assert res["ok"] and len(res["matches"]) == 2

def test_find_users_by_name_failure(monkeypatch):
    def fail(*a, **k):
        return {"ok": False, "error": "fail"}
    main.get_users = fail
    res = main.find_users_by_name("joe")
    assert "error" in res

# --- read_channel_messages ---
def test_read_channel_messages_expected():
    res = main.read_channel_messages(channel="C1")
    assert res["ok"] and isinstance(res["messages"], list)

def test_read_channel_messages_thread():
    res = main.read_channel_messages(channel="C1", thread_ts="123.456")
    assert res["ok"] and isinstance(res["messages"], list)

def test_read_channel_messages_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "conversations_history", fail)
    res = main.read_channel_messages(channel="C1")
    assert "error" in res

# --- search_messages ---
def test_search_messages_expected():
    res = main.search_messages(query="hi")
    assert res["ok"] and "matches" in res["messages"]

def test_search_messages_edge():
    res = main.search_messages(query="hi", count=1, page=2)
    assert res["ok"]

def test_search_messages_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "search_messages", fail)
    res = main.search_messages(query="fail")
    assert "error" in res

# --- create_channel ---
def test_create_channel_expected():
    res = main.create_channel(name="random")
    assert res["ok"] and res["channel"]["name"] == "random"

def test_create_channel_private():
    res = main.create_channel(name="secret", is_private=True)
    assert res["ok"]

def test_create_channel_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "conversations_create", fail)
    res = main.create_channel(name="fail")
    assert "error" in res

# --- invite_to_channel ---
def test_invite_to_channel_expected():
    res = main.invite_to_channel(channel="C1", users="U1,U2")
    assert res["ok"]

def test_invite_to_channel_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "conversations_invite", fail)
    res = main.invite_to_channel(channel="C1", users="U1")
    assert "error" in res

# --- upload_file ---
def test_upload_file_expected():
    res = main.upload_file(channels="C1", content="filedata", filename="doc.txt")
    assert res["ok"] and res["file"]["name"] == "doc.txt"

def test_upload_file_with_comment():
    res = main.upload_file(channels="C1", content="data", filename="img.png", initial_comment="Here")
    assert res["ok"]

def test_upload_file_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "files_upload", fail)
    res = main.upload_file(channels="C1", content="fail", filename="fail")
    assert "error" in res

# --- get_channel_info ---
def test_get_channel_info_expected():
    res = main.get_channel_info(channel="C1")
    assert res["ok"] and res["channel"]["id"] == "C1"

def test_get_channel_info_with_members():
    res = main.get_channel_info(channel="C1", include_num_members=True)
    assert res["ok"]

def test_get_channel_info_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "conversations_info", fail)
    res = main.get_channel_info(channel="C1")
    assert "error" in res

# --- update_message ---
def test_update_message_expected():
    res = main.update_message(channel="C1", ts="123.456", text="Updated!")
    assert res["ok"] and res["text"] == "Updated!"

def test_update_message_with_blocks():
    res = main.update_message(channel="C1", ts="123.456", text="Block!", blocks=[{"type": "section", "text": {"type": "plain_text", "text": "hi"}}])
    assert res["ok"]

def test_update_message_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "chat_update", fail)
    res = main.update_message(channel="C1", ts="fail", text="fail")
    assert "error" in res

# --- delete_message ---
def test_delete_message_expected():
    res = main.delete_message(channel="C1", ts="123.456")
    assert res["ok"] and res["ts"] == "123.456"

def test_delete_message_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "chat_delete", fail)
    res = main.delete_message(channel="C1", ts="fail")
    assert "error" in res

# --- get_user_info ---
def test_get_user_info_expected():
    res = main.get_user_info(user="U1")
    assert res["ok"] and res["profile"]["real_name"] == "Alice"

def test_get_user_info_failure(monkeypatch):
    def fail(*a, **k): raise Exception("fail")
    monkeypatch.setattr(main.slack_client, "users_profile_get", fail)
    res = main.get_user_info(user="fail")
    assert "error" in res
