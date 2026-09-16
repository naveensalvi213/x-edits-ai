import asyncio
from playwright.async_api import async_playwright

async def search_x_playwright():
    auth_token = "c6289fcc9d99ca623baba0a793c4a85a5be67af3"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        # Inject auth_token cookie
        await context.add_cookies([{
            "name": "auth_token",
            "value": auth_token,
            "domain": ".x.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }])
        
        page = await context.new_page()
        
        search_url = "https://x.com/search?q=%22hiring%20editor%22&f=live"
        print(f"Navigating to {search_url}...")
        
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        
        tweets = await page.query_selector_all('[data-testid="tweet"]')
        print(f"🎉 PLAYWRIGHT SUCCESS! FOUND {len(tweets)} TWEETS ON X!")
        
        for idx, t in enumerate(tweets[:5]):
            text_content = await t.inner_text()
            links = await t.query_selector_all('a[href*="/status/"]')
            link_url = ""
            for l in links:
                href = await l.get_attribute("href")
                if href and "/status/" in href:
                    link_url = f"https://x.com{href}"
                    break
            
            clean_text = " ".join(text_content.splitlines())
            print(f"[{idx+1}] {clean_text[:120]}... | Link: {link_url}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(search_x_playwright())
