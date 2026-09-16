import requests
import json
import urllib.parse

def test_gql_search():
    auth_token = "d6f44271b1b52711b81da7b176518efe14ce8916"
    
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    })
    s.cookies.set('auth_token', auth_token, domain='.x.com')
    s.get('https://x.com/i/flow/login')
    ct0 = s.cookies.get('ct0')
    if ct0:
        s.headers.update({'x-csrf-token': ct0})

    print(f"ct0 obtained: {bool(ct0)}")

    variables = {
        "rawQuery": "hiring editor",
        "count": 20,
        "querySource": "typed_query",
        "product": "Latest"
    }
    
    features = {
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_subscribable_bookmarks_is_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_media_due_to_visibility_risk": True,
        "responsive_web_enhance_cards_enabled": False
    }

    url = f"https://x.com/i/api/graphql/nK1FbB0vLEj3f7lQ5YyMvA/SearchTimeline?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}"
    
    res = s.get(url)
    print("GraphQL Status:", res.status_code)
    if res.status_code == 200:
        print("Success! Data keys:", list(res.json().keys()))
        data_str = res.text
        print("Response snippet:", data_str[:300])
    else:
        print("Error text:", res.text[:200])

if __name__ == "__main__":
    test_gql_search()
