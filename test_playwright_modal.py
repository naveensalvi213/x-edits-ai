import asyncio
from playwright.async_api import async_playwright

async def inspect_x_page():
    auth_token = "c6289fcc9d99ca623baba0a793c4a85a5be67af3"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        await context.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
            {"name": "auth_token", "value": auth_token, "domain": "x.com", "path": "/"}
        ])
        
        page = await context.new_page()
        print("Navigating to X search...")
        await page.goto("https://x.com/search?q=hiring%20editor&f=live", wait_until="domcontentloaded")
        
        try:
            print("Waiting for tweet cards to render...")
            await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            print(f"🎉 SUCCESS! FOUND {len(tweets)} TWEET CARDS!")
            for idx, t in enumerate(tweets[:3]):
                text = await t.inner_text()
                clean = " ".join(text.splitlines())
                print(f"[{idx+1}] {clean[:100]}...")
        except Exception as e:
            print("Selector wait failed:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_x_page())
