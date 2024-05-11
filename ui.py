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


def is_process_running(process_name):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            return True
    return False


class VideoDownloader:
    def __init__(self, root):
        self.style = tkb.Style()
        self.root = root
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        self.root.geometry('%dx%d+%d+%d' % (1100, 625, (screenwidth - 1100) / 2, (screenheight - 625) / 2))
        self.root.iconbitmap(r'.\tmp\favicon.ico')
        self.v, self.v0, self.folder_var, self.token = tkb.StringVar(), tkb.StringVar(), tkb.StringVar(), None
        self.flag = 1
        self.create_widgets()

    def create_widgets(self):
        # 主框架
        tab1 = tkb.Frame(self.root, width=1100, height=625)
        tab1.grid_propagate(False)
        tab1.pack()
        # 子框架1
        down_top_frame = tkb.Frame(tab1, width=875, height=625)
        down_top_frame.grid_propagate(False)
        down_top_frame.grid(row=0, column=0)
        title_frame = tkb.Frame(down_top_frame, width=800, height=80)
        title_frame.pack_propagate(False)
        title_frame.grid(row=0, pady=20)
        title = tkb.Label(title_frame, text='BiliBili Video Download', font=('Arial', 24, "bold"), foreground='Sky Blue')
        dividing_line1 = tkb.Separator(title_frame, bootstyle="primary")
        title.pack(anchor='w'), dividing_line1.pack(fill='x', pady=10)

        foundation_frame = tkb.LabelFrame(down_top_frame, text='基础', width=835, height=125, bootstyle="info")
        foundation_frame.grid_propagate(False)
        foundation_frame.grid(row=1, padx=20)
        file_save = tkb.Label(foundation_frame, text="保存地址: ", bootstyle="primary")
        self.folder_var.set(open(r'.\tmp\video_file.txt', 'r').read())
        self.entry2 = tkb.Entry(foundation_frame, width=55, textvariable=self.folder_var, state="readonly", bootstyle="primary")
        file_save.grid(row=0, column=0, padx=10, pady=5), self.entry2.grid(row=0, column=1, pady=5)
        down_options = tkb.Label(foundation_frame, text="下载选项: ", bootstyle="primary")
        self.combobox2 = tkb.Combobox(foundation_frame, values=["视频+音频", "仅音频", "快速下载"], state="readonly", bootstyle="primary")
        self.combobox2.current(0)
        down_options.grid(row=1, column=0, padx=10, pady=10), self.combobox2.grid(row=1, column=1, sticky='nsew', pady=10)
        save_button = tkb.Button(foundation_frame, text="-->", command=self.save_input, takefocus=False, width=5)
        open_button = tkb.Button(foundation_frame, text="open", command=self.open_input, takefocus=False, width=5)
        save_button.grid(row=0, column=2, padx=20), open_button.grid(row=0, column=3, padx=20)

        down_frame = tkb.LabelFrame(down_top_frame, text='下载', width=835, height=360, bootstyle="info")
        down_frame.pack_propagate(False)
        down_frame.grid(row=2, padx=20)

        url_frame = tkb.Frame(down_frame, width=835, height=120)
        url_frame.grid_propagate(False)
        url_frame.pack()
        down_url = tkb.Label(url_frame, text="视频地址: ", bootstyle="primary")
        self.entry = tkb.Entry(url_frame, width=60, bootstyle="primary")
        down_button = tkb.Button(url_frame, text="Down", width=10, command=self.process_input, takefocus=False)
        down_url.grid(row=0, column=0, padx=10), self.entry.grid(row=0, column=1), down_button.grid(row=0, column=2, padx=15)
        down_video_options = tkb.Label(url_frame, text="视频清晰度:", bootstyle="primary")
        self.combobox1 = tkb.Combobox(url_frame, values=["1080P", "720P", "360P"], state="readonly", bootstyle="primary")
        self.combobox1.current(0)
        down_video_options.grid(row=1, column=0, padx=5, pady=5), self.combobox1.grid(row=1, column=1, pady=5, sticky='nsew')
        self.mouse()  # 禁止鼠标滚轮控制选项

        log_frame = tkb.LabelFrame(down_frame, text='log', width=800, height=200, bootstyle="info")
        log_frame.pack_propagate(False)
        video_cover = tkb.Label(log_frame, text="视频标题: ????", bootstyle="primary")
        log_frame.pack(), video_cover.pack(padx=10, anchor='w')
        time_progress = tkb.Frame(log_frame, width=750, height=50)
        time_progress.pack_propagate(False)
        self.log_text = tkb.Label(time_progress, width=100, textvariable=self.v0, font=('黑体', 10), foreground='green')
        self.v0.set("下载状态")
        time_progress.pack(side='bottom', pady=10), self.log_text.pack(anchor='w')
        # 进度条
        self.progress = tkb.Progressbar(time_progress)

        # 子框架2
        tab1_top = tkb.Frame(tab1, width=225, height=635, relief='ridge')
        tab1_top.pack_propagate(False)
        tab1_top.grid(row=0, column=1)
        log_1 = tkb.Label(tab1_top, background="blue", width=60, textvariable=self.v, anchor='center', foreground='white')
        self.v.set('信息显示')
        button_verify = tkb.Button(tab1_top, text="验证", width=10, command=self.accept_input, takefocus=False)
        button_login = tkb.Button(tab1_top, text="登录", width=10, command=self.login_input, takefocus=False)
        log_1.pack(fill="x", side='top'), button_login.pack(pady=20), button_verify.pack()
        tab1_information = tkb.LabelFrame(tab1_top, text='img', width=200, height=200, borderwidth=2, relief="sunken")
        image = Image.open(r'.\tmp\0035.png')
        self.photo = ImageTk.PhotoImage(image)
        self.label = tkb.Label(tab1_information, image=self.photo)
        image_button = tkb.Button(tab1_top, text="清除缓存", command=self.login_accept, takefocus=False)
        topic = tkb.Checkbutton(tab1_top, text='dark', bootstyle="round-toggle", command=self.theme)
        tab1_information.pack(pady=30), self.label.pack(), image_button.pack(), topic.pack(side="bottom", pady=25)

    def run_quick_down(self, length, file_url, video_url):
        times = qd.quick_down(length, file_url, video_url)
        self.v0.set("快速下载完成,总用时: {:d}s".format(times))

    def run_quick_down_task(self, length, file_url, video_url):
        td.Thread(target=self.run_quick_down, args=(length, file_url, video_url)).start()

    def process_input(self):
        user_input = self.entry.get()
        definition = {"1080P": "80", "720P": "64", "360P": "16"}
        definition_input = definition[self.combobox1.get()]
        down_object = {"视频+音频": "0", "仅音频": "1", "快速下载": "2"}
        video_or_audio = down_object[self.combobox2.get()]
        if 'BV' in user_input:
            m = user_input[user_input.index('BV'):user_input.index('BV') + 12]
            m = "bvid=" + m[2:]
        elif 'av' in user_input:
            # m = user_input[user_input.index('av'):]
            temp = [i for i in user_input.split('/')]
            for i in temp:
                if 'av' in i:
                    m = i
                    break
        else:
            return self.v0.set("输入的地址中未包含BV或av号,请重新尝试")
        video_url, video_title, total = down.video_down(m, definition_input, video_or_audio)
        if video_title == "Warning_0":
            return self.v0.set(video_url)
        video = down.get_response(video_url, True)
        file_suffix = video_title + ".mp4"
        if video_or_audio == "1":
            self.v0.set("音频下载中...")
            file_suffix = video_title + ".mp3"
        elif video_or_audio == "0":
            self.v0.set("视频下载中...")
        else:
            self.v0.set("视频快速下载中...")
        length = int(video.headers.get('Content-Length'))
        if total == 0:
            length_block = int(length * 0.02) + 10000
            # 进度条
            self.progress['maximum'], self.progress['value'] = length, 0
            self.progress.pack(side='bottom', fill='x', pady=5)
            with open(self.entry2.get() + r'\{}'.format(file_suffix), 'wb') as f:
                # 获取下载进度
                start_time = time.time()
                write_all = 0
                for chunk in video.iter_content(chunk_size=length_block):
                    write_all += f.write(chunk)  # write的返回值为写入到文件内容的多少
                    self.progress['value'] = write_all
                    self.root.update()
            end_time = time.time()
            self.v0.set("下载完成,总用时: {:d}s".format(int(end_time - start_time)))
        else:
            file_url = self.entry2.get() + r'\{}'.format(file_suffix)
            self.run_quick_down_task(length, file_url, video_url)

    def mouse(self):
        def disable_scroll(event):
            return "break"

        self.combobox1.bind("<MouseWheel>", disable_scroll)
        self.combobox2.bind("<MouseWheel>", disable_scroll)

    #
    def save_input(self):
        file_path = filedialog.askdirectory()
        if file_path:
            self.folder_var.set(file_path)
            open(r'.\tmp\video_file.txt', "w").write(file_path)

    def open_input(self):
        folder_path = os.path.abspath(self.entry2.get())
        if os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            self.v0.set("所选保存路径不存在")

    def image_processing(self, image_file):
        image = Image.open(image_file)
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo)

    def accept_input(self):
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            self.v.set(verify.accept())
        else:
            self.v.set("未登录,请先登录")

    def theme(self):
        if self.flag == 1:
            self.style.theme_use('darkly')
            self.flag = 0
        else:
            self.style.theme_use('cosmo')
            self.flag = 1

    def thread_processing(self):
        self.v.set('已登录')
        self.image_processing(r'.\tmp\0035.png')

    def qrcode_thread(self):
        cut_time = 1
        while cut_time < 121:
            time.sleep(1)
            if cut_time % 5 == 0:
                if verify.login_accept(self.token) == "已登录":
                    self.root.after(0, self.thread_processing)
                    break
            cut_time += 1

    def login_input(self):
        self.token = verify.login()
        self.image_processing(r'.\tmp\my_blog.png')
        td.Thread(target=self.qrcode_thread).start()

    def login_accept(self):
        if os.path.isfile(r'.\tmp\my_blog.png'):
            os.remove(r'.\tmp\my_blog.png')
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            os.remove(r'.\tmp\your_cookie.txt')
        self.v.set('已清除缓存')


if __name__ == "__main__":
    if not is_process_running('BilibiliVideoDown.exe'):
        root = tkb.Window(title='Download UI', themename='cosmo', size=(1100, 625), resizable=(False, False))
        app = VideoDownloader(root)
        root.mainloop()