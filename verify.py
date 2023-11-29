import requests
import json
import qrcode
import cv2


def accept():
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": open(r'.\your_cookie.txt', 'r').read()
    }
    cookie_url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
    if json.loads(requests.get(url=cookie_url, headers=header).text)['code'] == 0:
        return "Cookie仍然可以生效"
    else:
        return "Cookie已过期,请重新获取"


def login():
    s = requests.Session()
    # 申请二维码
    url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
    }
    r = requests.get(url=url, headers=header)
    img_url = json.loads(r.text)['data']['url']
    token = json.loads(r.text)['data']['qrcode_key']
    # 生成二维码
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1
    )
    qr.add_data(img_url)
    qr.make(fit=True)
    img = qr.make_image()
    img.save("my_blog.png")
    # 显示二维码
    image = cv2.imread('my_blog.png')
    cv2.imshow("login", image)
    cv2.waitKey()
    # 扫码验证
    key_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
    kw = {'qrcode_key': token}
    key = s.get(url=key_url, params=kw, headers=header)
    if json.loads(key.text)['data']['message'] != '未扫码':
        key_cookie = key.headers['Set-Cookie']
        with open("your_cookie.txt", 'w') as f:
            f.write(key_cookie)
    else:
        return
