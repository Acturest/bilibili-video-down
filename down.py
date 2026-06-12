from pprint import pprint

import requests
import json
import os


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


def get_page_list(m):
    """根据 avid 或 bvid 返回分P列表，每个元素是 {'cid':xxx, 'part':'xxx'}"""
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
        pages = [{'cid': data['data']['cid'], 'part': data['data']['title']}]
    result = []
    for idx, page in enumerate(pages):
        result.append({
            'index': idx,
            'cid': page['cid'],
            'part': page['part']
        })
    return result


# 视频下载
def video_down(m, definition_id, audio_id, page_index=0):
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
