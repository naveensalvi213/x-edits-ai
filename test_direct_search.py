import requests
import json

def search_x_direct(query="hiring editor"):
    auth_token = "d6f44271b1b52711b81da7b176518efe14ce8916"
    
    session = requests.Session()
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    }
    session.headers.update(headers)
    session.cookies.set('auth_token', auth_token, domain='.x.com')
    
    # 1. Obtain ct0 CSRF token
    r_home = session.get('https://x.com/home')
    ct0 = session.cookies.get('ct0')
    if ct0:
        session.headers.update({'x-csrf-token': ct0})
        print(f"Success! Obtained ct0 token: {ct0[:15]}...")
    else:
        print("Failed to get ct0 token!")
        return

    # 2. Try GraphQL SearchTimeline endpoint
    params = {
        'variables': json.dumps({
            "rawQuery": query,
            "count": 20,
            "querySource": "typed_query",
            "product": "Latest"
        }),
        'features': json.dumps({
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "tweet_with_visibility_results_prefer_grok_responses": False,
            "c9s_tweet_anatomy_subscribable_bookmarks_is_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_media_due_to_visibility_risk": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False
        })
    }
    
    url = "https://x.com/i/api/graphql/nK1FbB0vLEj3f7lQ5YyMvA/SearchTimeline"
    res = session.get(url, params=params)
    print("GraphQL Search Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("Keys returned:", list(data.keys()))
        print("Successfully fetched search payload!")
    else:
        print("Response text:", res.text[:300])

if __name__ == "__main__":
    search_x_direct()
