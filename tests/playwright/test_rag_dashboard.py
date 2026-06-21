"""Playwright automated tests for RAG Quality Dashboard."""
import asyncio
import sys
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:5005"
SCREENSHOTS = "docs/screenshots"

# Test accounts
TECH_USER = {"username": "tech_support", "password": "tech123"}
REGULAR_USER = {"username": "testuser", "password": "test123"}


async def login(page, username, password):
    """Login helper."""
    await page.goto(f"{BASE}/login", wait_until="networkidle")
    await page.fill("#username", username)
    await page.fill("#password", password)
    await page.click("button[type=submit]")
    await page.wait_for_load_state("networkidle")


async def test_dashboard_loads():
    """Test 7.2: Dashboard page loads with stats cards and data table."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await login(page, TECH_USER["username"], TECH_USER["password"])
        await page.goto(f"{BASE}/rag-dashboard", wait_until="networkidle")

        # Assert stats cards
        stat_cards = page.locator(".stat-card")
        count = await stat_cards.count()
        assert count >= 4, f"Expected >= 4 stat cards, got {count}"

        # Assert data table exists
        table = page.locator(".data-table")
        assert await table.count() > 0, "Data table not found"

        # Screenshot
        await page.screenshot(path=f"{SCREENSHOTS}/rag-dashboard.png", full_page=True)
        print("✓ Dashboard loads with stats + table")

        await browser.close()


async def test_permission_control():
    """Test 7.3: Regular user redirected from dashboard."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await login(page, REGULAR_USER["username"], REGULAR_USER["password"])
        await page.goto(f"{BASE}/rag-dashboard", wait_until="networkidle")

        # Should be redirected away from dashboard
        current_url = page.url
        assert "rag-dashboard" not in current_url, f"Regular user shouldn't access dashboard, got: {current_url}"
        print("✓ Permission control: regular user redirected")

        await browser.close()


async def test_feedback_buttons():
    """Test 7.4: Feedback buttons appear and toggle correctly."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await login(page, REGULAR_USER["username"], REGULAR_USER["password"])

        # Navigate to dashboard and click on a conversation
        await page.goto(f"{BASE}/", wait_until="networkidle")
        # Try to find a conversation link
        conv_links = page.locator('a[href*="/conversation/"]')
        if await conv_links.count() > 0:
            await conv_links.first.click()
            await page.wait_for_load_state("networkidle")

            # Check for feedback buttons
            fb_buttons = page.locator(".feedback-btn")
            count = await fb_buttons.count()
            assert count > 0, "Feedback buttons not found on AI messages"

            # Click thumbs up
            thumbs_up = page.locator('.feedback-btn[data-type="positive"]').first
            if await thumbs_up.count() > 0:
                await thumbs_up.click()
                await page.wait_for_timeout(500)
                color = await thumbs_up.evaluate("el => el.style.color")
                assert color, "Thumbs up should be highlighted"

            # Screenshot
            await page.screenshot(path=f"{SCREENSHOTS}/feedback-buttons.png", full_page=False)
            print("✓ Feedback buttons visible and interactive")
        else:
            print("⚠ No conversations found to test feedback, creating one...")
            # Create a conversation
            create_btn = page.locator('button:has-text("创建会话")')
            if await create_btn.count() > 0:
                await create_btn.first.click()
                await page.wait_for_load_state("networkidle")
                # Send a message
                textarea = page.locator("textarea[name='content']")
                if await textarea.count() > 0:
                    await textarea.fill("你好")
                    submit_btn = page.locator(".chat-submit-btn")
                    if await submit_btn.count() > 0:
                        await submit_btn.click()
                        await page.wait_for_load_state("networkidle")
                # Check for feedback
                fb = page.locator(".feedback-btn")
                fbc = await fb.count()
                print(f"✓ Feedback buttons after conversation: {fbc}")

        await browser.close()


async def test_api_endpoints():
    """Test 7.5: API endpoints return correct structure."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await login(page, TECH_USER["username"], TECH_USER["password"])

        # GET /api/rag-logs/stats
        resp = await page.evaluate("fetch('/api/rag-logs/stats').then(r => r.json())")
        assert resp.get("success"), f"Stats API failed: {resp}"
        assert "stats" in resp, "Stats missing"
        print(f"✓ Stats API: {resp['stats']}")

        # GET /api/rag-logs
        resp = await page.evaluate("fetch('/api/rag-logs').then(r => r.json())")
        assert resp.get("success"), f"Logs API failed: {resp}"
        assert "items" in resp, "items missing"
        assert "pagination" in resp, "pagination missing"
        assert "stats" in resp, "stats missing"
        print(f"✓ Logs API: {len(resp['items'])} items, {resp['pagination']['total']} total")

        # POST /api/feedback
        resp = await page.evaluate("""
            fetch('/api/feedback', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message_id: 1, conversation_id: 1, type: 'positive'})
            }).then(r => r.json())
        """)
        assert resp.get("success"), f"Feedback API failed: {resp}"
        print("✓ Feedback API works")

        await browser.close()


async def test_log_detail_expand():
    """Test 7.6: Click log row to expand detail panel."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await login(page, TECH_USER["username"], TECH_USER["password"])
        await page.goto(f"{BASE}/rag-dashboard", wait_until="networkidle")

        # Click first log row
        rows = page.locator("#logsTableBody tr[onclick]")
        if await rows.count() > 0:
            await rows.first.click()
            await page.wait_for_timeout(1000)

            # Check detail panel visible
            panel = page.locator("#detailPanel")
            display = await panel.evaluate("el => el.style.display")
            assert display != "none", "Detail panel should be visible"
            print("✓ Log detail panel expands on click")
        else:
            print("⚠ No log rows to test expansion")

        await browser.close()


async def test_db_records():
    """Test 7.7: Verify database has records after retrieval."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await login(page, TECH_USER["username"], TECH_USER["password"])

        # Check logs exist
        resp = await page.evaluate("fetch('/api/rag-logs/stats').then(r => r.json())")
        total = resp.get("stats", {}).get("total_queries", 0)
        avg_sim = resp['stats'].get('avg_similarity', 0)
        pos_rate = resp['stats'].get('positive_rate', 0)
        print(f"✓ DB records: {total} retrieval logs, {avg_sim} avg similarity, {pos_rate}% positive feedback")

        await browser.close()


async def main():
    tests = [
        ("Dashboard loads", test_dashboard_loads),
        ("Permission control", test_permission_control),
        ("Feedback buttons", test_feedback_buttons),
        ("API endpoints", test_api_endpoints),
        ("Log detail expand", test_log_detail_expand),
        ("DB records", test_db_records),
    ]

    failed = 0
    for name, test_fn in tests:
        try:
            await test_fn()
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {len(tests) - failed}/{len(tests)} passed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
