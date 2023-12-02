import requests
import json
import qrcode
import cv2

header_public = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}


def accept():
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": open(r'.\tmp\your_cookie.txt', 'r').read()
    }
    cookie_url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    if json.loads(requests.get(url=cookie_url, headers=header).text)['code'] == 0:
        return "已登录(验证)"
    else:
        return "登录已过期,请尝试重新登录"


def login():
    # 申请二维码
    url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
    r = requests.get(url=url, headers=header_public)
    img_url = json.loads(r.text)['data']['url']
    token = json.loads(r.text)['data']['qrcode_key']
    # 生成二维码
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=1
    )
    qr.add_data(img_url)
    qr.make(fit=True)
    img = qr.make_image()
    img.save(r".\tmp\my_blog.png")
    return token


def login_accept(token):
    # 登录验证
    key_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
    kw = {'qrcode_key': token}
    key = requests.get(url=key_url, params=kw, headers=header_public)
    if json.loads(key.text)['data']['message'] != '未扫码':
        key_cookie = key.headers['Set-Cookie']
        with open(r".\tmp\your_cookie.txt", 'w') as f:
            f.write(key_cookie)
        return "已登陆"
    else:
        return "您似乎未扫码,请重新登录"
