import requests
import json
import os
global your_ck


# 发送请求
def get_response(html_url, temp):
    if os.path.isfile(r'.\tmp\your_cookie.txt'):
        cookie = open(r'.\tmp\your_cookie.txt', 'r').read()
    else:
        cookie = 'none cookie'
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookie
    }
    if not temp:
        r = requests.get(url=html_url, headers=header)
    else:
        r = requests.get(url=html_url, headers=header, stream=True)
    return r


# 视频下载
def video_down(m, definition_id, audio_id):
    if m[0:2] == 'av':
        m, p = "avid=" + m[2:], "aid=" + m[2:]
        # 获取视频cid
        cid = "https://api.bilibili.com/x/web-interface/view?{}".format(p)
    else:
        cid = "https://api.bilibili.com/x/web-interface/view?{}".format(m)
    cid_url = get_response(cid, False)
    if json.loads(cid_url.text)['code'] != 0:
        return "Warning:地址有误(av/BV号存在错误)或视频不见了", "Warning_0"
    video_cid = json.loads(cid_url.text)["data"]["cid"]
    # 获取视频标题
    sets = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    video_title = json.loads(cid_url.text)["data"]["title"]
    for char in video_title:
        if char in sets:
            video_title = video_title.replace(char, ' ')
    # 下载音频
    if audio_id == '1':
        audio_api = "https://api.bilibili.com/x/player/wbi/playurl?{}&cid={}&qn={}&fnval={}&fnver={}&fourk={}".format(m, video_cid, "0", "80", "0", "1")
        audio_text = get_response(audio_api, False)
        audio_url = json.loads(audio_text.text)['data']['dash']['audio'][0]['baseUrl']
        return audio_url, video_title
    # 下载视频
    video_api = "https://api.bilibili.com/x/player/playurl?{}&cid={}&qn={}".format(m, video_cid, definition_id)
    video_text = get_response(video_api, False)
    video_url = json.loads(video_text.text)['data']['durl'][0]['url']
    return video_url, video_title

