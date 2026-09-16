import asyncio
import requests
from twikit import Client

async def test_search():
    auth_token = "c6289fcc9d99ca623baba0a793c4a85a5be67af3"
    
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    })
    s.cookies.set('auth_token', auth_token, domain='.x.com')
    s.get('https://x.com')
    
    cookies = dict(s.cookies)
    print("Session cookies retrieved:", list(cookies.keys()))
    
    client = Client('en-US')
    client.set_cookies(cookies)
    
    try:
        tweets = await client.search_tweet('hiring editor', 'Latest')
        print(f"🎉 SUCCESS! Found {len(tweets)} tweets!")
        for t in tweets[:3]:
            user_name = t.user.screen_name if t.user else "unknown"
            print(f"- @{user_name}: {t.text[:80]}...")
    except Exception as e:
        print(f"Error searching with twikit: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
