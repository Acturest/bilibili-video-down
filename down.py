import requests
import json
import os
import re
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


def vid_params(m: str) -> tuple:
    """
    把各种写法的视频号统一成接口参数。
    接受: 'BV1cZHK65ELz' / 'bvid=BV1cZHK65ELz' / 'av12345' / 'aid=12345' / 'avid=12345'
    返回: (view 接口参数, playurl 接口参数)，无法识别时返回 (None, None)
    """
    s = (m or '').strip()
    for pref in ('bvid=', 'avid=', 'aid='):
        if s[:len(pref)].lower() == pref:
            s = s[len(pref):]
            break
    if s.startswith('BV'):
        s = s[:12]
        return 'bvid=' + s, 'bvid=' + s
    num = s[2:] if s.startswith('av') else s
    if num.isdigit():
        return 'aid=' + num, 'avid=' + num
    return None, None


def get_page_list(m: str) -> list:
    """根据 BV 号 / av 号返回分P列表，每个元素是 {'index','cid','part','duration'}"""
    view_param, _ = vid_params(m)
    if not view_param:
        return []
    cid_url = "https://api.bilibili.com/x/web-interface/view?{}".format(view_param)
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


_ILLEGAL_CHARS = set('<>:"/\\|?*')
_RESERVED_NAMES = ({'CON', 'PRN', 'AUX', 'NUL'}
                   | {'COM%d' % i for i in range(1, 10)}
                   | {'LPT%d' % i for i in range(1, 10)})


def safe_filename(name: str, max_len: int = 120) -> str:
    """
    把视频标题（含分P名）变成 Windows 合法文件名。
    分P名常含 '/'，直接当路径用会被当成子目录，导致
    FileNotFoundError；另外控制字符、结尾的点/空格、保留名（CON 等）也一并处理。
    """
    s = ''.join(' ' if (c in _ILLEGAL_CHARS or ord(c) < 32) else c
                for c in (name or ''))
    s = re.sub(r' {2,}', ' ', s).strip().strip('.')
    if s.split('.')[0].upper() in _RESERVED_NAMES:
        s = '_' + s
    if len(s) > max_len:
        s = s[:max_len].rstrip('. ')
    return s or 'video'


# 清晰度 ID → 名称（B 站 qn 编码）
QUALITY_NAMES = {
    6: '240P', 16: '360P', 32: '480P', 64: '720P', 74: '720P60',
    80: '1080P', 112: '1080P+', 116: '1080P60', 120: '4K',
    125: 'HDR', 126: '杜比视界', 127: '8K',
}


def quality_name(qid) -> str:
    try:
        return QUALITY_NAMES.get(int(qid or 0), '未知({})'.format(qid))
    except (TypeError, ValueError):
        return '未知({})'.format(qid)


def _playurl(play_param: str, cid, qn, dash: bool = True) -> dict:
    """
    请求播放地址。
    dash=True 时带 fnval=4048（DASH + 4K/HDR/杜比/8K 能力位）：
    没有 fnval 时 B 站只返回 durl（老接口），最高只给 720P，
    请求 1080P 会被静默降级成 720P —— 这正是"选了 1080P 却下到 720P"的原因。
    """
    url = "https://api.bilibili.com/x/player/playurl?{}&cid={}&qn={}".format(
        play_param, cid, qn)
    if dash:
        url += "&fnval=4048&fnver=0&fourk=1"
    return json.loads(get_response(url, False).text)


def _pick_video(dash: dict, qn: int):
    """在 dash.video 里挑出目标清晰度：精确匹配优先，否则取不超过目标的最高一档。"""
    videos = dash.get('video') or []
    if not videos:
        return None
    want = int(qn or 0)
    ids = sorted({v.get('id') or 0 for v in videos}, reverse=True)
    if want in ids:
        target = want
    else:
        lower = [i for i in ids if i <= want]
        target = lower[0] if lower else ids[-1]
    pool = [v for v in videos if (v.get('id') or 0) == target]
    # 同一清晰度通常有 AVC/HVC/AV1 多条，优先 AVC（兼容性最好），再取码率低的
    pool.sort(key=lambda v: (0 if v.get('codecid') == 7 else 1,
                             v.get('bandwidth') or 0))
    return pool[0]


def _pick_audio(dash: dict):
    audios = dash.get('audio') or []
    if not audios:
        return None
    audios.sort(key=lambda a: (a.get('bandwidth') or 0), reverse=True)
    return audios[0]


def _stream_url(track: dict) -> str:
    return track.get('baseUrl') or track.get('base_url') or ''


# 视频下载
def video_down(m: str, definition_id: str, audio_id: str, page_index: int = 0) -> tuple:
    """
    获取视频/音频下载地址。
    清晰度 qn 参数: 16=360P, 32=480P, 64=720P, 80=1080P,
                      116=1080P60, 120=4K, 125=4K, 126=HDR
    返回 (video_url, video_title, total, audio_url, info)
      - audio_url 非空表示 DASH 音视频分离，调用方需用 ffmpeg 合并
      - total: 0=普通单线程, 1=可多线程加速（durl 或 DASH 分片均可）
      - info: 实际取到的清晰度等，B 站可能因权限降级
    """
    view_param, play_param = vid_params(m)
    if not view_param:
        return ("Warning:地址有误,无法识别的视频号", "Warning_0", 0, '', {})
    # 获取视频cid
    cid = "https://api.bilibili.com/x/web-interface/view?{}".format(view_param)
    cid_url = get_response(cid, False)
    if json.loads(cid_url.text)['code'] != 0:
        return ("Warning:地址有误(av/BV号存在错误)或视频不见了", "Warning_0",
                0, '', {})
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
    video_title = json.loads(cid_url.text)["data"]["title"]
    # 单P视频的 part 名和标题常常完全一样，直接拼会出现「标题_标题.mp4」，
    # 所以只有分P名确实不同才拼接（净化前后都比一次，"a/b" vs "a／b" 这类也算重复）。
    if part_name:
        _p_raw, _p_clean = part_name.strip(), safe_filename(part_name).strip()
        if _p_raw and _p_raw != video_title.strip() and _p_clean != safe_filename(video_title).strip():
            video_title = video_title + '_' + part_name
    # 先拼再统一净化（分P名里的 '/' 也必须替换，否则会被当成子目录）
    video_title = safe_filename(video_title)

    info = {'requested': int(definition_id or 0),
            'requested_name': quality_name(definition_id),
            'quality_id': 0, 'quality': '未知',
            'height': 0, 'accept': [], 'mode': ''}

    # 仅音频：只要 DASH 音频轨
    if audio_id == '1':
        data = _playurl(play_param, video_cid, 0, dash=True)
        if data.get('code') != 0:
            return ("Warning:{}".format(data.get('message')), "Warning_0",
                    0, '', info)
        track = _pick_audio((data.get('data') or {}).get('dash') or {})
        if not track:
            return "Warning:该视频取不到音频流（可能需要登录）", "Warning_0", 0, '', info
        info.update(quality_id=0, quality='音频',
                    accept=(data.get('data') or {}).get('accept_description', []),
                    mode='dash-audio')
        return _stream_url(track), video_title, 0, '', info

    # 视频+音频 / 快速下载：先按 DASH 请求（1080P 及以上只有 DASH 才有）
    data = _playurl(play_param, video_cid, definition_id, dash=True)
    if data.get('code') != 0:
        return ("Warning:{}".format(data.get('message')), "Warning_0", 0, '', info)

    payload = data.get('data') or {}
    dash = payload.get('dash') or {}
    track = _pick_video(dash, definition_id)
    if track:
        audio = _pick_audio(dash)
        info.update(quality_id=track.get('id'),
                    quality=quality_name(track.get('id')),
                    height=track.get('height') or 0,
                    accept=payload.get('accept_description') or [],
                    mode='dash')
        return (_stream_url(track), video_title,
                1 if audio_id == '2' else 0,
                _stream_url(audio) if audio else '',
                info)

    # 回退：少数老视频没有 DASH，只能走 durl（最高 720P，内含音轨）
    legacy = _playurl(play_param, video_cid, definition_id, dash=False)
    payload = legacy.get('data') or {}
    durl = payload.get('durl') or []
    if legacy.get('code') != 0 or not durl:
        return ("Warning:没有取到可用的视频流（可能需要登录或大会员）",
                "Warning_0", 0, '', info)
    info.update(quality_id=payload.get('quality'),
                quality=quality_name(payload.get('quality')),
                accept=payload.get('accept_description') or [],
                mode='durl')
    return (durl[0]['url'], video_title, 1 if audio_id == '2' else 0, '', info)
