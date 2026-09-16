import asyncio
import requests
from twikit import Client

async def search_x():
    auth_token = "d6f44271b1b52711b81da7b176518efe14ce8916"
    
    session = requests.Session()
    session.headers.update({'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    session.cookies.set('auth_token', auth_token, domain='.x.com')
    
    response = session.get('https://x.com/home')
    cookies = dict(session.cookies)
    print(f"Fetched session cookies from X. CT0 present: {'ct0' in cookies}")
    
    client = Client('en-US')
    client.set_cookies(cookies)
    
    tweets = await client.search_tweet('hiring editor', 'Latest')
    print(f"🎉 SUCCESS! Found {len(tweets)} tweets via auth_token!")
    for t in tweets[:3]:
        username = t.user.screen_name if t.user else "unknown"
        print(f"👉 @{username}: {t.text[:100]}...")

if __name__ == "__main__":
    asyncio.run(search_x())
