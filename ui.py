from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import down
import verify
import time
import os


class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title('Down Video')
        self.root.geometry('350x350+362+234')
        self.root["bg"] = "white"
        # 虚化 值越小虚化程度越高
        # self.root.attributes('-alpha', 0.8)
        # GUI components
        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        # 创建选项卡1
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text='登录&验证')
        self.v, self.v0, self.folder_var = StringVar(), StringVar(), StringVar()
        top_1 = Label(tab1, bg='yellow', width=60, textvariable=self.v)
        self.v.set('验证以及登录的信息将显示在这里')
        button_verify = ttk.Button(tab1, text="验证", width=10, command=self.accept_input)
        button_login = ttk.Button(tab1, text="登录", width=10, command=self.login_input)
        top_1.pack(fill="both", side='bottom')
        button_login.pack(), button_verify.pack()
        # 创建选项卡2
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text='下载视频')
        text1 = ttk.Label(tab2, text="视频地址(支持av号):")
        self.entry = ttk.Entry(tab2, width=60)
        text2 = ttk.Label(tab2, text="视频清晰度:")
        options1 = ["1080P", "720P", "360P"]
        self.combobox1 = ttk.Combobox(tab2, values=options1)
        self.combobox1.current(0)
        text3 = ttk.Label(tab2, text="下载选项:")
        options2 = ["视频+音频", "仅音频"]
        self.combobox2 = ttk.Combobox(tab2, values=options2)
        self.combobox2.current(0)
        text4 = ttk.Label(tab2, text="视频保存地址")
        self.folder_var.set(open(r'.\tmp\video_file.txt', 'r').read())
        self.entry2 = ttk.Entry(tab2, width=80, textvariable=self.folder_var, state="readonly")
        save_button = ttk.Button(tab2, text="save", command=self.save_input)
        open_button = ttk.Button(tab2, text="open", command=self.open_input)
        # 禁止鼠标滚轮控制选项
        self.mouse()
        button = ttk.Button(tab2, text="下载", width=10, command=self.process_input)
        self.text_log = Label(tab2, bg='yellow', width=100, textvariable=self.v0)
        self.v0.set("这里将显示部分错误信息以及下载状态")
        # 进度条
        self.progress = ttk.Progressbar(tab2)
        # 放置主窗口
        text1.pack(side="top", anchor='nw'), self.entry.pack(fill="both")
        text2.pack(side="top", anchor='w'), self.combobox1.pack(side="top", anchor='w')
        text3.pack(side="top", anchor='w'), self.combobox2.pack(side="top", anchor='w')
        text4.pack(side="top", anchor='w'), self.entry2.pack(side="top", anchor='w'),
        save_button.pack(side="top", anchor='w'), open_button.pack(side="top", anchor='w')
        button.pack(padx=5, pady=5)
        self.text_log.pack(fill="both", side='bottom')
        notebook.pack(side="top", fill="both", expand=True)

    def process_input(self):
        user_input = self.entry.get()
        definition = {"1080P": "80", "720P": "64", "360P": "16"}
        definition_input = definition[self.combobox1.get()]
        down_object = {"视频+音频": "0", "仅音频": "1"}
        downloadtheobject = down_object[self.combobox2.get()]
        if 'BV' in user_input:
            m = user_input[user_input.index('BV'):user_input.index('BV') + 12]
            m = "bvid=" + m[2:]
        elif 'av' in user_input:
            m = user_input[user_input.index('av'):user_input.index('av') + 11]
        else:
            return self.v0.set("输入的地址中未包含BV或av号,请重新尝试")
        video_url, video_title = down.video_down(m, definition_input)
        if video_title == "Warning_0":
            return self.v0.set(video_url)
        video = down.get_response(video_url, True)
        length = int(video.headers.get('Content-Length'))
        length_to = int(length*0.02)+10000
        # 进度条
        self.v0.set("视频下载中...")
        self.progress['maximum'], self.progress['value'] = length, 0
        self.progress.pack(pady=10)
        with open(self.entry2.get()+r'\{}.mp4'.format(video_title), 'wb') as f:
            # 获取下载进度
            start_time = time.time()
            write_all = 0
            for chunk in video.iter_content(chunk_size=length_to):
                write_all += f.write(chunk)  # write的返回值为写入到文件内容的多少
                self.progress['value'] = write_all
                self.root.update()
        end_time = time.time()
        self.v0.set("视频下载完成,总用时: {:d}s".format(int(end_time - start_time)))

    def accept_input(self):
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            self.v.set(verify.accept())
        else:
            self.v.set("未登录,请先登录")

    def login_input(self):
        self.v.set(verify.login())

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
