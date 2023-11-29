from tkinter import *
from tkinter import ttk
import down
import verify
import time
import os


class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title('Down Video')
        self.root.geometry('350x300+362+234')
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
        self.v = StringVar()
        top_1 = Label(tab1, bg='yellow', width=60, textvariable=self.v)
        self.v.set('未验证')
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
        button = ttk.Button(tab2, text="下载", width=10, command=self.process_input)
        # 进度条
        self.progress = ttk.Progressbar(tab2)
        # 放置主窗口
        text1.pack(side="top", anchor='nw'), self.entry.pack(fill="both")
        text2.pack(side="top", anchor='w'), self.combobox1.pack(side="top", anchor='w')
        text3.pack(side="top", anchor='w'), self.combobox2.pack(side="top", anchor='w')
        button.pack(padx=5, pady=5)
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
        video_url, video_title = down.video_down(m, definition_input)
        video = down.get_response(video_url, True)
        length = int(video.headers.get('Content-Length'))
        # 进度条
        self.progress['maximum'] = length
        self.progress['value'] = 0
        self.progress.pack(pady=10)
        with open(r'.\{}.mp4'.format(video_title), 'wb') as f:
            # 获取下载进度
            start_time = time.time()
            write_all = 0
            for chunk in video.iter_content(chunk_size=1000):
                write_all += f.write(chunk)  # write的返回值为写入到文件内容的多少
                self.progress['value'] = write_all
                self.root.update()
                # time.sleep(0.05)
        end_time = time.time()
        print('Time : ', int(end_time - start_time))

    def accept_input(self):
        if os.path.isfile(r'.\tmp\your_cookie.txt'):
            self.v.set(verify.accept())
        else:
            self.v.set("未登录,请先登录")

    def login_input(self):
        verify.login()


if __name__ == "__main__":
    root = Tk()
    app = VideoDownloader(root)
    root.mainloop()
