import requests
import json

def test_x_search():
    auth_token = "d6f44271b1b52711b81da7b176518efe14ce8916"
    
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    })
    s.cookies.set('auth_token', auth_token, domain='x.com')
    
    # Get ct0 from login flow
    s.get('https://x.com/i/flow/login')
    ct0 = s.cookies.get('ct0')
    if not ct0:
        s.cookies.set('auth_token', auth_token, domain='.x.com')
        s.get('https://x.com/home')
        ct0 = s.cookies.get('ct0')

    if ct0:
        s.headers.update({'x-csrf-token': ct0})
        print(f"Session initialized with ct0: {ct0[:20]}...")
    else:
        print("Failed to get ct0!")
        return

    # Query search
    url = "https://x.com/i/api/2/search/adaptive.json"
    params = {
        'include_profile_interstitial_type': '1',
        'include_blocking': '1',
        'include_blocked_by': '1',
        'include_followed_by': '1',
        'include_want_retweets': '1',
        'include_mute_edge': '1',
        'include_can_dm': '1',
        'include_can_media_tag': '1',
        'include_ext_has_nft_avatar': '1',
        'include_ext_is_blue_verified': '1',
        'include_ext_verified_type': '1',
        'skip_status': '1',
        'cards_platform': 'Web-12',
        'include_cards': '1',
        'include_ext_alt_text': 'true',
        'include_ext_limited_action_results': 'false',
        'include_quote_count': 'true',
        'include_reply_count': '1',
        'tweet_mode': 'extended',
        'include_ext_views': 'true',
        'q': 'hiring editor',
        'count': '20',
        'query_source': 'typed_query',
        'tweet_search_mode': 'live'
    }

    res = s.get(url, params=params)
    print("Search Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        tweets = data.get("globalObjects", {}).get("tweets", {})
        users = data.get("globalObjects", {}).get("users", {})
        print(f"🎉 SUCCESS! Found {len(tweets)} tweets directly via auth_token cookie!")
        for tid, t in list(tweets.items())[:3]:
            uid = t.get("user_id_str")
            username = users.get(uid, {}).get("screen_name", "unknown")
            text = t.get("full_text", "")
            print(f"- @{username} (ID: {tid}): {text[:100]}...")
    else:
        print("Response text:", res.text[:200])

if __name__ == "__main__":
    test_x_search()
