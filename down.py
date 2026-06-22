import requests
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = BASE_DIR
DATA_DIR = os.path.join(APP_DIR, 'tmp')
os.makedirs(DATA_DIR, exist_ok=True)


# 发送请求
def get_response(html_url: str, temp: bool) -> requests.Response:
    cookie_path = os.path.join(DATA_DIR, 'your_cookie.txt')
    if os.path.isfile(cookie_path):
        lines = open(cookie_path, 'r').readlines()
        cookie = ''.join(line for line in lines if not line.startswith('#'))
    else:
        cookie = 'none cookie'
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookie
    }
    try:
        if not temp:
            r = requests.get(url=html_url, headers=header, timeout=30)
        else:
            r = requests.get(url=html_url, headers=header, stream=True, timeout=30)
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        raise RuntimeError(f"请求失败: {html_url} — {e}")


def get_page_list(m: str) -> list:
    """根据 avid 或 bvid 返回分P列表，每个元素是 {'cid':xxx, 'part':'xxx', 'duration':123}"""
    if m[0:2] == 'av':
        p = "aid=" + m[2:]
    else:
        p = "bvid=" + m
    cid_url = "https://api.bilibili.com/x/web-interface/view?{}".format(p)
    resp = get_response(cid_url, False)
    data = json.loads(resp.text)
    if data['code'] != 0:
        return []
    pages = data['data'].get('pages', [])
    # 兼容单P（无pages字段时自己构造一个）
    if not pages:
        pages = [{
            'cid': data['data']['cid'],
            'part': data['data']['title'],
            'duration': data['data'].get('duration', 0)
        }]
    result = []
    for idx, page in enumerate(pages):
        result.append({
            'index': idx,
            'cid': page['cid'],
            'part': page['part'],
            'duration': page.get('duration', 0)
        })
    return result


# 视频下载
def video_down(m: str, definition_id: str, audio_id: str, page_index: int = 0) -> tuple:
    """
    获取视频/音频下载地址。
    清晰度 qn 参数: 16=360P, 32=480P, 64=720P, 80=1080P,
                      116=1080P60, 120=1080P高帧率, 125=4K, 126=HDR
    """
    if m[0:2] == 'av':
        m, p = "avid=" + m[2:], "aid=" + m[2:]
        # 获取视频cid
        cid = "https://api.bilibili.com/x/web-interface/view?{}".format(p)
    else:
        cid = "https://api.bilibili.com/x/web-interface/view?{}".format(m)
    cid_url = get_response(cid, False)
    if json.loads(cid_url.text)['code'] != 0:
        return "Warning:地址有误(av/BV号存在错误)或视频不见了", "Warning_0"
    # pprint(cid_url.text)
    #原逻辑 video_cid = json.loads(cid_url.text)["data"]["cid"]
    # video_cid = json.loads(cid_url.text)["data"]["pages"][13]['cid']

    pages = json.loads(cid_url.text)["data"].get("pages", [])
    if pages:
        video_cid = pages[page_index]['cid']
        part_name = pages[page_index].get('part', '')
    else:
        video_cid = json.loads(cid_url.text)["data"]["cid"]
        part_name = ''

    # 获取视频标题
    sets = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    video_title = json.loads(cid_url.text)["data"]["title"]
    for char in video_title:
        if char in sets:
            video_title = video_title.replace(char, ' ')

    if part_name:
        video_title = video_title + '_' + part_name

    # 下载音频
    if audio_id == '1':
        audio_api = "https://api.bilibili.com/x/player/wbi/playurl?{}&cid={}&qn={}&fnval={}&fnver={}&fourk={}".format(m, video_cid, "0", "80", "0", "1")
        audio_text = get_response(audio_api, False)
        audio_url = json.loads(audio_text.text)['data']['dash']['audio'][0]['baseUrl']
        return audio_url, video_title, 0
    # 下载视频
    if audio_id == '0':
        video_api = "https://api.bilibili.com/x/player/playurl?{}&cid={}&qn={}".format(m, video_cid, definition_id)
        video_text = get_response(video_api, False)

        video_url = json.loads(video_text.text)['data']['durl'][0]['url']
        return video_url, video_title, 0
    else:
        video_api = "https://api.bilibili.com/x/player/playurl?{}&cid={}&qn={}".format(m, video_cid, definition_id)
        video_text = get_response(video_api, False)
        video_url = json.loads(video_text.text)['data']['durl'][0]['url']
        return video_url, video_title, 1
