from curl_cffi import requests
import json

def test_curl_cffi():
    auth_token = "c6289fcc9d99ca623baba0a793c4a85a5be67af3"
    
    s = requests.Session(impersonate="chrome120")
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
        'x-twitter-active-user': 'yes',
        'x-twitter-client-language': 'en',
    })
    s.cookies.set('auth_token', auth_token, domain='.x.com')
    
    res_home = s.get('https://x.com')
    cookies_dict = dict(s.cookies)
    ct0 = cookies_dict.get('ct0')
    print("ct0 retrieved:", bool(ct0), f"value: {ct0[:15] if ct0 else 'None'}")
    
    if ct0:
        s.headers.update({'x-csrf-token': ct0})

    url = "https://x.com/i/api/2/search/adaptive.json"
    params = {
        'q': 'hiring editor',
        'count': '20',
        'query_source': 'typed_query',
        'tweet_search_mode': 'live'
    }

    res = s.get(url, params=params)
    print("Search Status:", res.status_code)
    if res.status_code == 200:
        print("🎉 BOOM! SUCCESS WITH CURL_CFFI TLS IMPERSONATION!")
        data = res.json()
        tweets = data.get("globalObjects", {}).get("tweets", {})
        print("TWEETS COUNT:", len(tweets))
        for tid, t in list(tweets.items())[:3]:
            print(f"- {tid}: {t.get('full_text', '')[:100]}...")
    else:
        print("Error text:", res.text[:300])

if __name__ == "__main__":
    test_curl_cffi()
