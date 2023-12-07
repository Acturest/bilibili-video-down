from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading as td
import down
import verify
import time
import os


class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title('Down Video')
        self.root.geometry('350x380+362+234')
        self.root["bg"] = "white"
        self.v, self.v0, self.folder_var, self.token = StringVar(), StringVar(), StringVar(), None
        # 虚化 值越小虚化程度越高
        # self.root.attributes('-alpha', 0.8)
        # GUI components
        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        # 选项卡1
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text='登录&验证')
        tab1_top = ttk.Frame(tab1)
        button_verify = ttk.Button(tab1_top, text="验证", width=10, command=self.accept_input, takefocus=False)
        button_login = ttk.Button(tab1_top, text="登录", width=10, command=self.login_input, takefocus=False)
        tab1_information = ttk.LabelFrame(tab1, text='二维码', width=200, height=200, borderwidth=2, relief="sunken")
        image = Image.open(r'.\tmp\0035.png')
        self.photo = ImageTk.PhotoImage(image)
        self.label = ttk.Label(tab1_information, image=self.photo)
        image_button = ttk.Button(tab1_information, text="清除缓存", command=self.login_accept, takefocus=False)
        log_1 = ttk.Label(tab1, background="yellow", width=60, textvariable=self.v, anchor='center')
        self.v.set('验证以及登录的信息将显示在这里')
        tab1_top.pack(pady=10), button_login.grid(row=0, column=0, padx=10), button_verify.grid(row=0, column=1, padx=10)
        tab1_information.pack(), self.label.pack(), image_button.pack()
        log_1.pack(fill="both", side='bottom')
        # 选项卡2
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text='下载视频')
        text1 = ttk.Label(tab2, text="视频地址(支持av号):")
        self.entry = ttk.Entry(tab2, width=60)
        text2 = ttk.Label(tab2, text="视频清晰度:")
        options1 = ["1080P", "720P", "360P"]
        self.combobox1 = ttk.Combobox(tab2, values=options1, state="readonly")
        self.combobox1.current(0)
        text3 = ttk.Label(tab2, text="下载选项:")
        options2 = ["视频+音频", "仅音频"]
        self.combobox2 = ttk.Combobox(tab2, values=options2, state="readonly")
        self.combobox2.current(0)
        text4 = ttk.Label(tab2, text="文件保存地址:")
        self.folder_var.set(open(r'.\tmp\video_file.txt', 'r').read())
        self.entry2 = ttk.Entry(tab2, width=80, textvariable=self.folder_var, state="readonly")
        file_button = ttk.Frame(tab2)
        save_button = ttk.Button(file_button, text="选择保存位置", command=self.save_input, takefocus=False)
        open_button = ttk.Button(file_button, text="打开文件地址", command=self.open_input, takefocus=False)
        # 禁止鼠标滚轮控制选项
        self.mouse()
        down_button = ttk.Button(tab2, text="下载", width=10, command=self.process_input, takefocus=False)
        log_2 = ttk.Label(tab2, background="yellow", width=100, textvariable=self.v0, anchor='center')
        self.v0.set("这里将显示部分错误信息以及下载状态")
        # 进度条
        self.progress = ttk.Progressbar(tab2)
        # 放置主窗口
        text1.pack(side="top", anchor='nw'), self.entry.pack(fill="both")
        text2.pack(side="top", anchor='w'), self.combobox1.pack(side="top", anchor='w')
        text3.pack(side="top", anchor='w'), self.combobox2.pack(side="top", anchor='w')
        text4.pack(side="top", anchor='w'), self.entry2.pack(side="top", anchor='w'),
        file_button.pack(), save_button.grid(row=0, column=0, padx=40), open_button.grid(row=0, column=1, padx=40)
        down_button.pack(padx=5, pady=5)
        log_2.pack(fill="both", side='bottom')
        notebook.pack(side="top", fill="both", expand=True)

    def process_input(self):
        user_input = self.entry.get()
        definition = {"1080P": "80", "720P": "64", "360P": "16"}
        definition_input = definition[self.combobox1.get()]
        down_object = {"视频+音频": "0", "仅音频": "1"}
        video_or_audio = down_object[self.combobox2.get()]
        if 'BV' in user_input:
            m = user_input[user_input.index('BV'):user_input.index('BV') + 12]
            m = "bvid=" + m[2:]
        elif 'av' in user_input:
            m = user_input[user_input.index('av'):user_input.index('av') + 11]
        else:
            return self.v0.set("输入的地址中未包含BV或av号,请重新尝试")
        video_url, video_title = down.video_down(m, definition_input, video_or_audio)
        if video_title == "Warning_0":
            return self.v0.set(video_url)
        video = down.get_response(video_url, True)
        file_suffix = video_title + ".mp4"
        if video_or_audio == "1":
            self.v0.set("音频下载中...")
            file_suffix = video_title + ".mp3"
        else:
            self.v0.set("视频下载中...")
        length = int(video.headers.get('Content-Length'))
        length_block = int(length * 0.02) + 10000
        # 进度条
        self.progress['maximum'], self.progress['value'] = length, 0
        self.progress.pack(pady=10)
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

    def image_processing(self, image_file):
        image = Image.open(image_file)
        self.photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self.photo)

    def accept_input(self):
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            self.v.set(verify.accept())
        else:
            self.v.set("未登录,请先登录")

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
        t1 = td.Thread(target=self.qrcode_thread).start()

    def login_accept(self):
        if os.path.isfile(r'.\tmp\my_blog.png'):
            os.remove(r'.\tmp\my_blog.png')
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            os.remove(r'.\tmp\your_cookie.txt')
        self.v.set('已清除缓存')

    def mouse(self):
        def disable_scroll(event):
            return "break"

        self.combobox1.bind("<MouseWheel>", disable_scroll)
        self.combobox2.bind("<MouseWheel>", disable_scroll)

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


if __name__ == "__main__":
    root = Tk()
    app = VideoDownloader(root)
    root.mainloop()
