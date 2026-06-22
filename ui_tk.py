from tkinter import filedialog
import ttkbootstrap as tkb
from PIL import Image, ImageTk
import threading as td
import psutil
import down
import quick_down as qd
import verify
import time
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def is_process_running(process_name):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            return True
    return False


class VideoDownloader:
    def __init__(self, root: tkb.Window) -> None:
        self.style = tkb.Style()
        self.root = root
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        self.root.geometry('1100x650+%d+%d' % ((screenwidth - 1100) // 2, (screenheight - 650) // 2))
        self.root.iconbitmap(os.path.join(BASE_DIR, 'tmp', 'favicon.ico'))
        self.v, self.v0, self.folder_var, self.token = tkb.StringVar(), tkb.StringVar(), tkb.StringVar(), None
        self.flag = 1
        self.page_list = []  # 存储当前视频的分P列表
        self.page_combobox = None  # 分P下拉框对象
        self.create_widgets()

    # ── Layout builders ──────────────────────────────────────────────────

    def create_widgets(self) -> None:
        """Build the modern responsive UI layout."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_container = tkb.Frame(self.root)
        main_container.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0, minsize=230)
        main_container.rowconfigure(0, weight=1)

        # Left panel — main content
        left_panel = tkb.Frame(main_container)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(3, weight=1)  # download area expands

        self._build_title(left_panel)
        self._build_settings(left_panel)
        self._build_download_area(left_panel)

        # Right sidebar
        right_panel = tkb.Frame(main_container, width=230)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        right_panel.grid_propagate(False)

        self._build_sidebar(right_panel)

        self.mouse()  # disable scrollwheel on comboboxes

    def _build_title(self, parent: tkb.Frame) -> None:
        """Title and separator."""
        title = tkb.Label(parent, text='BiliBili Video Download',
                          font=('Arial', 22, 'bold'), bootstyle='primary')
        title.grid(row=0, column=0, sticky='w', pady=(0, 5))
        separator = tkb.Separator(parent, bootstyle='primary')
        separator.grid(row=1, column=0, sticky='ew', pady=(0, 10))

    def _build_settings(self, parent: tkb.Frame) -> None:
        """Settings card: save path + download mode."""
        frame = tkb.LabelFrame(parent, text='设置', bootstyle='info', padding=10)
        frame.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        # Save path row
        tkb.Label(frame, text='保存地址:', bootstyle='primary')\
            .grid(row=0, column=0, padx=(0, 5), pady=4, sticky='w')
        try:
            saved_path = open(os.path.join(BASE_DIR, 'tmp', 'video_file.txt'), 'r').read()
        except FileNotFoundError:
            saved_path = os.path.expanduser('~\\Downloads')
        self.folder_var.set(saved_path)
        self.entry2 = tkb.Entry(frame, textvariable=self.folder_var,
                                state='readonly', bootstyle='primary')
        self.entry2.grid(row=0, column=1, sticky='ew', padx=(0, 5), pady=4)
        tkb.Button(frame, text='📂 选择', command=self.save_input,
                   takefocus=False, bootstyle='info-outline')\
            .grid(row=0, column=2, padx=(0, 2), pady=4)
        tkb.Button(frame, text='📁 打开', command=self.open_input,
                   takefocus=False, bootstyle='info-outline')\
            .grid(row=0, column=3, pady=4)

        # Download mode row
        tkb.Label(frame, text='下载选项:', bootstyle='primary')\
            .grid(row=1, column=0, padx=(0, 5), pady=4, sticky='w')
        self.combobox2 = tkb.Combobox(
            frame, values=['视频+音频', '仅音频', '快速下载'],
            state='readonly', bootstyle='primary')
        self.combobox2.current(0)
        self.combobox2.grid(row=1, column=1, sticky='ew', padx=(0, 5), pady=4)

    def _build_download_area(self, parent: tkb.Frame) -> None:
        """Download card: URL, quality, page selector, status, progress."""
        frame = tkb.LabelFrame(parent, text='下载', bootstyle='info', padding=10)
        frame.grid(row=3, column=0, sticky='nsew')
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        # URL input + action buttons
        tkb.Label(frame, text='视频地址:', bootstyle='primary')\
            .grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        self.entry = tkb.Entry(frame, bootstyle='primary')
        self.entry.grid(row=0, column=1, sticky='ew', padx=(0, 5), pady=5)
        btn_frame = tkb.Frame(frame)
        btn_frame.grid(row=0, column=2, pady=5)
        tkb.Button(btn_frame, text='🔍 获取分P', command=self.fetch_pages,
                   takefocus=False, bootstyle='info-outline')\
            .pack(side='left', padx=(0, 3))
        tkb.Button(btn_frame, text='⬇ 下载', command=self.process_input,
                   takefocus=False, bootstyle='success')\
            .pack(side='left')

        # Quality selector
        tkb.Label(frame, text='视频清晰度:', bootstyle='primary')\
            .grid(row=1, column=0, padx=(0, 5), pady=4, sticky='w')
        self.combobox1 = tkb.Combobox(
            frame, values=['1080P', '720P', '360P'],
            state='readonly', bootstyle='primary')
        self.combobox1.current(0)
        self.combobox1.grid(row=1, column=1, sticky='ew', padx=(0, 5), pady=4)

        # Page selector
        tkb.Label(frame, text='分P选择:', bootstyle='primary')\
            .grid(row=2, column=0, padx=(0, 5), pady=4, sticky='w')
        self.page_combobox = tkb.Combobox(
            frame, values=['请先获取分P'], state='readonly', bootstyle='primary')
        self.page_combobox.current(0)
        self.page_combobox.grid(row=2, column=1, sticky='ew', padx=(0, 5), pady=4)

        # Status label
        self.v0.set('就绪')
        tkb.Label(frame, textvariable=self.v0,
                  font=('微软雅黑', 10), bootstyle='primary')\
            .grid(row=3, column=0, columnspan=3, sticky='w', pady=(5, 2))

        # Floodgauge animated progress bar
        self.progress = tkb.Floodgauge(
            frame, bootstyle='info', mask=' 已下载 {} B')
        self.progress.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(0, 5))

        # ScrolledText log area
        self.log_text_widget = tkb.ScrolledText(
            frame, height=5)
        self.log_text_widget.grid(row=5, column=0, columnspan=3, sticky='nsew', pady=(0, 5))
        self.log_text_widget.insert('end', '就绪\n')
        self.log_text_widget.configure(state='disabled')  # read-only

    def _build_sidebar(self, parent: tkb.Frame) -> None:
        """Sidebar: login, cover image, theme toggle."""
        # ── Login card ──
        login_frame = tkb.LabelFrame(parent, text='登录', bootstyle='info', padding=8)
        login_frame.pack(fill='x', pady=(0, 8))

        self.v.set('信息显示')
        tkb.Label(login_frame, textvariable=self.v, bootstyle='primary')\
            .pack(anchor='w', pady=(0, 8))

        tkb.Button(login_frame, text='扫描二维码登录', command=self.login_input,
                   takefocus=False, bootstyle='primary')\
            .pack(fill='x', pady=(0, 4))
        tkb.Button(login_frame, text='验证登录状态', command=self.accept_input,
                   takefocus=False, bootstyle='info-outline')\
            .pack(fill='x')

        # ── Cover image card ──
        img_frame = tkb.LabelFrame(parent, text='封面', bootstyle='info', padding=5)
        img_frame.pack(fill='x', pady=(0, 8))

        image_path = os.path.join(BASE_DIR, 'tmp', '0035.png')
        if os.path.isfile(image_path):
            image = Image.open(image_path)
            self.photo = ImageTk.PhotoImage(image)
            self.label = tkb.Label(img_frame, image=self.photo)
        else:
            self.label = tkb.Label(img_frame, text='暂无封面',
                                   anchor='center', bootstyle='secondary')
        self.label.pack(fill='x')

        # ── Clear cache ──
        tkb.Button(parent, text='清除缓存', command=self.login_accept,
                   takefocus=False, bootstyle='warning-outline')\
            .pack(fill='x', pady=(0, 8))

        # ── Theme toggle ──
        theme_frame = tkb.Frame(parent)
        theme_frame.pack(side='bottom', fill='x', pady=(0, 5))
        tkb.Label(theme_frame, text='深色模式', bootstyle='primary')\
            .pack(side='left')
        self.theme_toggle = tkb.Checkbutton(
            theme_frame, bootstyle='round-toggle', command=self.theme)
        self.theme_toggle.pack(side='right')

    def log_append(self, message: str) -> None:
        """Append a timestamped message to the ScrolledText log."""
        timestamp = time.strftime('%H:%M:%S')
        self.log_text_widget.configure(state='normal')
        self.log_text_widget.insert('end', '[{}] {}\n'.format(timestamp, message))
        self.log_text_widget.see('end')  # auto-scroll
        self.log_text_widget.configure(state='disabled')

    def run_quick_down(self, length: int, file_url: str, video_url: str) -> None:
        times = qd.quick_down(length, file_url, video_url)
        msg = "快速下载完成,总用时: {:d}s".format(times)
        self.v0.set(msg)
        self.log_append(msg)

    def run_quick_down_task(self, length: int, file_url: str, video_url: str) -> None:
        self.v0.set("快速下载已启动，后台多线程下载中...")
        self.log_append("快速下载已启动（后台多线程）")
        td.Thread(target=self.run_quick_down, args=(length, file_url, video_url)).start()

    def process_input(self):
        try:
            self._do_process_input()
        except RuntimeError as e:
            self.v0.set(str(e))
            self.log_append("错误: " + str(e))

    def _parse_vid(self, user_input: str):
        """从用户输入的URL中解析vid，返回 (vid_or_None, error_msg_or_None)"""
        if 'BV' in user_input:
            m = user_input[user_input.index('BV'):user_input.index('BV') + 12]
            return "bvid=" + m[2:], None
        elif 'av' in user_input:
            av_match = re.search(r'(?:/|^)(av\d+)', user_input)
            if av_match:
                return av_match.group(1), None
            return None, "无法从地址中识别av号，请检查格式"
        else:
            return None, "输入的地址中未包含BV或av号,请重新尝试"

    def fetch_pages(self) -> None:
        """点击'获取'按钮：解析vid并拉取分P列表"""
        user_input = self.entry.get()
        m, err = self._parse_vid(user_input)
        if err:
            return self.v0.set(err)
        from down import get_page_list
        pages = get_page_list(m)
        if not pages:
            return self.v0.set("获取分P信息失败，请检查地址")
        self.page_list = pages
        for p in self.page_list:
            p['_input'] = m
        page_names = ["{}. {}".format(p['index'] + 1, p['part']) for p in pages]
        self.page_combobox['values'] = page_names
        self.page_combobox.current(0)
        self.v0.set("已获取分P列表，请选择分P后点击下载")
        self.log_append("已获取 {} 个分P".format(len(pages)))

    def _do_process_input(self) -> None:
        """点击 Down：直接使用已获取的分P列表下载"""
        if self.page_combobox is None:
            return self.v0.set("请先点击'获取'拉取分P列表")

        user_input = self.entry.get()
        definition = {"1080P": "80", "720P": "64", "360P": "16"}
        definition_input = definition[self.combobox1.get()]
        down_object = {"视频+音频": "0", "仅音频": "1", "快速下载": "2"}
        video_or_audio = down_object[self.combobox2.get()]

        m, err = self._parse_vid(user_input)
        if err:
            return self.v0.set(err)

        # 检查分P列表是否已获取
        if not self.page_list:
            return self.v0.set("请先点击'获取'拉取分P列表")

        # 使用选中的分P索引下载
        selected_idx = self.page_combobox.current()
        if selected_idx < 0 or selected_idx >= len(self.page_list):
            return self.v0.set("分P选择无效，请重新选择")
        page_index = self.page_list[selected_idx]['index']

        # 调用修改后的 video_down，传入 page_index
        video_url, video_title, total = down.video_down(m, definition_input, video_or_audio, page_index)
        if video_title == "Warning_0":
            return self.v0.set(video_url)
        video = down.get_response(video_url, True)

        file_suffix = video_title + ".mp4"
        if video_or_audio == "1":
            self.v0.set("音频下载中...")
            file_suffix = video_title + ".mp3"
            self.log_append("开始下载音频: " + video_title)
        elif video_or_audio == "0":
            self.v0.set("视频下载中...")
            self.log_append("开始下载视频: " + video_title)
        else:
            self.v0.set("视频快速下载中...")
            self.log_append("开始快速下载: " + video_title)
        length = int(video.headers.get('Content-Length'))
        if total == 0:
            length_block = int(length * 0.02) + 10000
            self.progress.configure(maximum=length, value=0)
            self.progress.start()  # animate while downloading
            with open(self.entry2.get() + r'\{}'.format(file_suffix), 'wb') as f:
                start_time = time.time()
                write_all = 0
                for chunk in video.iter_content(chunk_size=length_block):
                    write_all += f.write(chunk)
                    self.progress.configure(value=write_all)
                    self.root.update()
            self.progress.stop()
            self.progress.configure(value=0)
            end_time = time.time()
            msg = "下载完成,总用时: {:d}s".format(int(end_time - start_time))
            self.v0.set(msg)
            self.log_append(msg)
        else:
            file_url = self.entry2.get() + r'\{}'.format(file_suffix)
            self.run_quick_down_task(length, file_url, video_url)

    def mouse(self) -> None:
        def disable_scroll(event):
            return "break"

        self.combobox1.bind("<MouseWheel>", disable_scroll)
        self.combobox2.bind("<MouseWheel>", disable_scroll)

        if self.page_combobox:
            self.page_combobox.bind("<MouseWheel>", disable_scroll)

    def save_input(self) -> None:
        file_path = filedialog.askdirectory()
        if file_path:
            self.folder_var.set(file_path)
            open(os.path.join(BASE_DIR, 'tmp', 'video_file.txt'), "w").write(file_path)

    def open_input(self) -> None:
        folder_path = os.path.abspath(self.entry2.get())
        if os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            self.v0.set("所选保存路径不存在")

    def image_processing(self, image_file: str) -> None:
        image = Image.open(image_file)
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo)

    def accept_input(self) -> None:
        if os.path.isfile(os.path.join(BASE_DIR, 'tmp', 'your_cookie.txt')):
            self.v.set(verify.accept())
        else:
            self.v.set("未登录,请先登录")

    def theme(self) -> None:
        if self.flag == 1:
            self.style.theme_use('superhero')
            self.flag = 0
        else:
            self.style.theme_use('cosmo')
            self.flag = 1

    def thread_processing(self) -> None:
        self.v.set('已登录')
        self.image_processing(os.path.join(BASE_DIR, 'tmp', '0035.png'))

    def qrcode_thread(self) -> None:
        cut_time = 1
        while cut_time < 121:
            time.sleep(1)
            if cut_time % 5 == 0:
                if verify.login_accept(self.token) == "已登录":
                    self.root.after(0, self.thread_processing)
                    break
            cut_time += 1

    def login_input(self) -> None:
        self.token = verify.login()
        self.image_processing(os.path.join(BASE_DIR, 'tmp', 'my_blog.png'))
        td.Thread(target=self.qrcode_thread).start()

    def login_accept(self) -> None:
        if os.path.isfile(os.path.join(BASE_DIR, 'tmp', 'my_blog.png')):
            os.remove(os.path.join(BASE_DIR, 'tmp', 'my_blog.png'))
        if os.path.isfile(os.path.join(BASE_DIR, 'tmp', 'your_cookie.txt')):
            os.remove(os.path.join(BASE_DIR, 'tmp', 'your_cookie.txt'))
        self.v.set('已清除缓存')


if __name__ == "__main__":
    if not is_process_running('BilibiliVideoDown.exe'):
        root = tkb.Window(title='Download UI', themename='cosmo', size=(1100, 650), resizable=(True, True))
        app = VideoDownloader(root)
        root.mainloop()