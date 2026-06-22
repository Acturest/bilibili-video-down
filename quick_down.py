import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = BASE_DIR
DATA_DIR = os.path.join(APP_DIR, 'tmp')
os.makedirs(DATA_DIR, exist_ok=True)


def calc_divisional_range(file_size: int, chuck: int = 10) -> list:
    step = file_size // chuck
    arr = list(range(0, file_size, step))
    result = []
    for i in range(len(arr) - 1):
        s_pos, e_pos = arr[i], arr[i + 1] - 1
        result.append([s_pos, e_pos])
    result[-1][-1] = file_size - 1
    return result


def range_download(save_file: str, url: str, s_pos: int, e_pos: int) -> None:
    cookie_path = os.path.join(DATA_DIR, 'your_cookie.txt')
    if os.path.isfile(cookie_path):
        lines = open(cookie_path, 'r').readlines()
        cookie = ''.join(line for line in lines if not line.startswith('#'))
    else:
        cookie = 'none cookie'
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookie,
        "Range": f"bytes={s_pos}-{e_pos}"
    }
    res = requests.get(url=url, headers=headers, stream=True)
    with open(save_file, "rb+") as f:
        f.seek(s_pos)
        for chunk in res.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)


def quick_down(file_size: int, file: str, url: str) -> int:
    # 切片
    ranges = calc_divisional_range(file_size)
    # 创建
    with open(file, "wb") as f:
        pass
    # 下载
    start = time.time()
    with ThreadPoolExecutor() as p:
        futures = []
        for s_pos, e_pos in ranges:
            futures.append(p.submit(range_download, file, url, s_pos, e_pos))
        # 等待所有任务执行完毕
        as_completed(futures)
    end = time.time()
    return int(end - start)
