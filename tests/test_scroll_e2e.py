import re
import pytest
import threading
import time
import uvicorn
from app.main import app
from playwright.async_api import async_playwright, expect

SERVER_PORT = 8008


@pytest.fixture(scope="module", autouse=True)
def run_test_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    time.sleep(1)  # wait for server to start
    yield
    server.should_exit = True


@pytest.mark.asyncio
async def test_scroll_to_bottom_button_e2e():
    """Playwright E2E test verifying floating scroll button behavior."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.route("**/api/auth/status", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"authenticated": true, "username": "testuser"}'
        ))
        await page.route("**/api/sessions", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"id": "sess-1", "title": "Test Chat", "created_at": "2026-01-01T00:00:00Z"}]'
        ))
        await page.route("**/api/sessions/sess-1/history", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[]'
        ))

        await page.goto(f"http://127.0.0.1:{SERVER_PORT}")

        # Hide auth modal explicitly
        await page.evaluate("""() => {
            const modal = document.getElementById('auth-modal');
            if (modal) modal.style.display = 'none';
        }""")

        chat_container = page.locator("#chat-container")
        await expect(chat_container).to_be_visible()

        # Fill chat-container with 30 message items to force scrolling
        await page.evaluate("""() => {
            const container = document.getElementById('chat-container');
            container.innerHTML = '';
            for (let i = 0; i < 30; i++) {
                const div = document.createElement('div');
                div.className = 'message ai-message';
                div.innerHTML = `<div class="message-bubble" style="padding: 20px;">Message ${i}</div>`;
                container.appendChild(div);
            }
        }""")

        scroll_btn = page.locator("#scroll-to-bottom-btn")

        # 1. Scrolled to bottom initially: button should NOT have class 'visible'
        await page.evaluate("""() => {
            const c = document.getElementById('chat-container');
            c.scrollTop = c.scrollHeight;
            c.dispatchEvent(new Event('scroll'));
        }""")
        await expect(scroll_btn).not_to_have_class(re.compile(r"visible"))

        # 2. Scroll up to top: button MUST have class 'visible'
        await page.evaluate("""() => {
            const c = document.getElementById('chat-container');
            c.scrollTop = 0;
            c.dispatchEvent(new Event('scroll'));
        }""")
        await expect(scroll_btn).to_have_class(re.compile(r"visible"))

        # 3. Click button: scroll back to bottom
        await scroll_btn.click()

        # 4. Verify button becomes hidden again after scrolling to bottom
        await expect(scroll_btn).not_to_have_class(re.compile(r"visible"))

        # 5. Verify scrolled to bottom
        is_at_bottom = await page.wait_for_function("""() => {
            const c = document.getElementById('chat-container');
            return Math.abs(c.scrollHeight - c.scrollTop - c.clientHeight) <= 50;
        }""")
        assert is_at_bottom

        await browser.close()
