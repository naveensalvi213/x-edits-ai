import requests

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
})
s.cookies.set('auth_token', 'd6f44271b1b52711b81da7b176518efe14ce8916', domain='x.com')

r = s.get('https://x.com/i/flow/login')
print("Login flow cookies:", dict(s.cookies))

r2 = s.get('https://x.com/home')
print("Home cookies:", dict(s.cookies))
