import asyncio
from twikit import Client

async def test_login():
    username = "neothumbnailss"
    passwords = ["neo_thumbnailssA1", "neo_newA1"]
    
    for pwd in passwords:
        client = Client('en-US')
        print(f"Attempting login for @{username} with password: {pwd[:3]}***")
        try:
            await client.login(auth_info_1=username, password=pwd)
            print(f"🎉 SUCCESS! Logged in successfully with password: {pwd}")
            
            # Save cookies to file for persistent sessions
            client.save_cookies('cookies.json')
            print("Saved session cookies to cookies.json!")
            
            # Test search
            tweets = await client.search_tweet('hiring editor', 'Latest')
            print(f"🔥 SEARCH SUCCESS! Found {len(tweets)} tweets!")
            for t in tweets[:3]:
                user_name = t.user.screen_name if t.user else "unknown"
                print(f"- @{user_name}: {t.text[:80]}...")
            return True
        except Exception as e:
            print(f"❌ Login failed with password '{pwd}': {e}")
            
    return False

if __name__ == "__main__":
    asyncio.run(test_login())
