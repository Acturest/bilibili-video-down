import requests
import json
import qrcode
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = BASE_DIR
DATA_DIR = os.path.join(APP_DIR, 'tmp')
os.makedirs(DATA_DIR, exist_ok=True)

header_public = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}


def accept() -> str:
    header = dict(header_public)
    header["Cookie"] = ''.join(
        line for line in open(os.path.join(DATA_DIR, 'your_cookie.txt'), 'r')
        if not line.startswith('#')
    )
    cookie_url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    if json.loads(requests.get(url=cookie_url, headers=header).text)['code'] == 0:
        return "已登录(验证)"
    else:
        return "登录已过期,请尝试重新登录"


def login() -> str:
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
    img.save(os.path.join(DATA_DIR, 'my_blog.png'))
    return token


def login_accept(token: str) -> str:
    # 登录验证
    key_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
    kw = {'qrcode_key': token}
    key = requests.get(url=key_url, params=kw, headers=header_public)
    if json.loads(key.text)['data']['message'] != '未扫码' and 'Set-Cookie' in key.headers:
        key_cookie = key.headers['Set-Cookie']
        with open(os.path.join(DATA_DIR, 'your_cookie.txt'), 'w') as f:
            f.write("# 警告: 此文件包含你的B站登录凭证(Cookie)，请勿分享给他人！\n")
            f.write(key_cookie)
        return "已登录"
    else:
        return "您似乎未扫码,请重新登录"
