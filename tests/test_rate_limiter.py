from slack_mcp.rate_limiter import SlackRateLimiter
import time

def test_rate_limiter_blocks_and_eta():
    rl = SlackRateLimiter()
    method = "chat_postMessage"

    # First call should go through
    called = []
    def f():
        called.append(1)
        return {"ok": True}
    result1 = rl.wrap(method, f)
    assert result1["ok"]
    assert called == [1]

    # Simulate a 429 response with Retry-After 2 seconds
    def f429():
        return {"error": "ratelimited", "retry_after": 2}
    result2 = rl.wrap(method, f429)
    assert result2["error"] == "ratelimited"
    assert result2["retry_after"] == 2
    assert "eta" in result2 and result2["eta"]

    # Now, while rate-limited, any call should return the same info (without calling f)
    called.clear()
    result3 = rl.wrap(method, f)
    assert result3["error"] == "ratelimited"
    assert result3["retry_after"] <= 2
    assert "eta" in result3 and result3["eta"]
    assert called == []

    # After waiting, call should go through again
    time.sleep(2.1)
    result4 = rl.wrap(method, f)
    assert result4["ok"]
    assert called == [1]

    # Also test exception path (simulate SlackApiError with 429)
    class DummyResp:
        status_code = 429
        headers = {"Retry-After": "1"}
    class DummyExc(Exception):
        def __init__(self):
            self.response = DummyResp()
    def f_exc():
        raise DummyExc()
    result5 = rl.wrap(method, f_exc)
    assert result5["error"] == "ratelimited"
    assert result5["retry_after"] == 1
    assert "eta" in result5 and result5["eta"]
