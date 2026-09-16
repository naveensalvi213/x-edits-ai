import requests
import json

def run_test():
    auth_token = "c6289fcc9d99ca623baba0a793c4a85a5be67af3"
    
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    s.cookies.set('auth_token', auth_token, domain='.x.com')
    res_home = s.get('https://x.com/home')
    
    cookies_dict = dict(s.cookies)
    ct0 = cookies_dict.get('ct0')
    print(f"ct0 Token: {ct0[:20] if ct0 else 'NONE'}")

    s.headers.update({
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
        'x-csrf-token': ct0,
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    })

    url = "https://x.com/i/api/2/search/adaptive.json"
    params = {
        'q': 'hiring editor',
        'count': '20',
        'query_source': 'typed_query',
        'tweet_search_mode': 'live'
    }
    
    res_search = s.get(url, params=params)
    print("Adaptive Search Status:", res_search.status_code)
    if res_search.status_code == 200:
        data = res_search.json()
        tweets = data.get("globalObjects", {}).get("tweets", {})
        users = data.get("globalObjects", {}).get("users", {})
        print(f"🎉 SUCCESS! Found {len(tweets)} live posts!")
        for tid, t in list(tweets.items())[:5]:
            uid = t.get("user_id_str")
            username = users.get(uid, {}).get("screen_name", "unknown")
            text = t.get("full_text", "")
            print(f"- @{username}: {text[:100]}...")
    else:
        print("Error:", res_search.text[:300])

if __name__ == "__main__":
    run_test()
