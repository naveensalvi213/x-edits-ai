import asyncio
from twikit import Client

async def main():
    client = Client('en-US')
    client.set_cookies({'auth_token': 'd6f44271b1b52711b81da7b176518efe14ce8916'})
    try:
        tweets = await client.search_tweet('hiring editor', 'Latest')
        print(f"Found {len(tweets)} tweets!")
        for t in tweets[:3]:
            print(f"- @{t.user.name} ({t.user.screen_name}): {t.text[:80]}...")
    except Exception as e:
        print(f"Error searching tweets: {e}")

if __name__ == "__main__":
    asyncio.run(main())
