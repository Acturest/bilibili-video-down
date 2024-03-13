import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os


def calc_divisional_range(file_size, chuck=10):
    step = file_size // chuck
    arr = list(range(0, file_size, step))
    result = []
    for i in range(len(arr) - 1):
        s_pos, e_pos = arr[i], arr[i + 1] - 1
        result.append([s_pos, e_pos])
    result[-1][-1] = file_size - 1
    return result


def range_download(save_file, url, s_pos, e_pos):
    if os.path.isfile(r'.\tmp\your_cookie.txt'):
        cookie = open(r'.\tmp\your_cookie.txt', 'r').read()
    else:
        cookie = 'none cookie'
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
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


def quick_down(file_size, file, url):
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
