"""
BiliBili Video Downloader — MSFluentWindow + 3-interface layout
"""
import sys
import os
import time
import re
import json
import shutil
import subprocess
import threading as td

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (QApplication, QFrame, QVBoxLayout,
                             QHBoxLayout, QFileDialog, QSizePolicy)

from PIL import Image
from io import BytesIO

from qfluentwidgets import (MSFluentWindow, NavigationItemPosition,
                            PrimaryPushButton, PushButton, ComboBox,
                            LineEdit, ProgressBar, SwitchButton,
                            SimpleCardWidget, PlainTextEdit,
                            BodyLabel, SpinBox,
                            setTheme, Theme, FluentIcon as FIF)

import down
import quick_down as qd
import verify
import psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── 防止长文本撑宽窗口的小工具 ────────────────────────────────────────
def brief(text, limit: int = 160) -> str:
    """状态栏文本截断，避免超长路径/异常信息把窗口横向撑开。"""
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def elide_text(text, limit: int = 70) -> str:
    """下拉框条目截断显示（完整分P信息仍保存在 page_list 里）。"""
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def status_label(text: str = ''):
    """不随文本变宽的状态标签：横向策略 Ignored，超出宽度换行或裁剪。"""
    label = BodyLabel(text)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    label.setMinimumWidth(0)
    return label


class ElidedComboBox(ComboBox):
    """
    ComboBox 内部是 QPushButton，宽度会跟着最长条目文本一起变大，
    长分P名能把整个窗口撑宽。让 sizeHint 固定，条目文本另行截断。
    """

    def sizeHint(self):
        return QSize(200, super().sizeHint().height())

    def minimumSizeHint(self):
        return QSize(80, super().minimumSizeHint().height())

# App directory — when PyInstaller-bundled use exe's location, else script dir
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = BASE_DIR

DATA_DIR = os.path.join(APP_DIR, 'tmp')
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def is_process_running(process_name):
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            return True
    return False


# ── Helper: parse vid ──────────────────────────────────────────────────
def parse_vid(user_input: str):
    """从地址中提取裸号：'BV1cZHK65ELz' 或 'av12345'（不带 bvid=/aid= 前缀）。"""
    if 'BV' in user_input:
        idx = user_input.index('BV')
        m = user_input[idx:idx + 12]          # BV + 10 位，共 12 个字符
        return m, None
    elif 'av' in user_input:
        match = re.search(r'(?:/|^)(av\d+)', user_input)
        if match:
            return match.group(1), None
        return None, '无法从地址中识别av号，请检查格式'
    return None, '输入的地址中未包含BV或av号,请重新尝试'


# ── Download Interface ─────────────────────────────────────────────────
class DownloadInterface(QFrame):
    def __init__(self, text: str, main=None):
        super().__init__(parent=main)
        self.main = main
        self._setup_ui()
        self.setObjectName(text.replace(' ', '-'))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── URL row ──
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        url_label = BodyLabel('视频地址:')
        url_label.setFixedWidth(70)
        self.url_edit = LineEdit()

        btn_paste = PushButton('📋 粘贴')
        btn_paste.clicked.connect(self.main._on_paste_url)
        btn_fetch = PushButton('🔍 获取分P')
        btn_fetch.clicked.connect(self.main._on_fetch_pages)
        btn_download = PrimaryPushButton('⬇ 下载')
        btn_download.clicked.connect(self.main._on_download_clicked)

        url_row.addWidget(url_label)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(btn_paste)
        url_row.addWidget(btn_fetch)
        url_row.addWidget(btn_download)
        layout.addLayout(url_row)

        # ── Option cards row (quality | mode) ──
        opt_row = QHBoxLayout()
        opt_row.setSpacing(10)

        def make_option_card(items, default_index, label, attr_name):
            card = SimpleCardWidget()
            cl = QHBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(6)
            cl.addWidget(BodyLabel(label))
            combo = ComboBox()
            combo.addItems(items)
            combo.setCurrentIndex(default_index)
            cl.addWidget(combo)
            setattr(self, attr_name, combo)
            return card

        opt_row.addWidget(make_option_card(
            ['1080P60', '1080P高帧率', '1080P', '720P', '360P'], 0, '视频清晰度:', 'quality_combo'))
        opt_row.addWidget(make_option_card(
            ['视频+音频', '仅音频', '快速下载'], 0, '下载选项:', 'mode_combo'))
        layout.addLayout(opt_row)

        # ── Page selector row (separate line for long titles) ──
        page_row = QHBoxLayout()
        page_row.setSpacing(6)
        page_label = BodyLabel('分P选择:')
        page_label.setFixedWidth(70)
        self.page_combo = ElidedComboBox()
        self.page_combo.addItems(['请先获取分P'])
        self.page_combo.setCurrentIndex(0)
        page_row.addWidget(page_label)
        page_row.addWidget(self.page_combo, 1)
        layout.addLayout(page_row)

        # ── Status ──
        self.download_status = status_label('就绪')
        layout.addWidget(self.download_status)

        # ── Progress ──
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(22)
        layout.addWidget(self.progress_bar)

        # ── Log ──
        self.log_text = PlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        self.log_text.setPlaceholderText('操作日志...')
        self.log_text.setMinimumHeight(100)
        layout.addWidget(self.log_text, 1)


# ── Info Interface ─────────────────────────────────────────────────────
class InfoInterface(QFrame):
    def __init__(self, text: str, main=None):
        super().__init__(parent=main)
        self.main = main
        self._setup_ui()
        self.setObjectName(text.replace(' ', '-'))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # ── Login card ──
        login_card = SimpleCardWidget()
        login_layout = QVBoxLayout(login_card)
        login_layout.setContentsMargins(16, 16, 16, 16)
        login_layout.setSpacing(8)

        self.sidebar_info = status_label('信息显示')
        login_layout.addWidget(self.sidebar_info)

        btn_login = PrimaryPushButton('扫描二维码登录')
        btn_login.clicked.connect(self.main._on_login_clicked)
        login_layout.addWidget(btn_login)

        btn_verify = PushButton('验证登录状态')
        btn_verify.clicked.connect(self.main._on_verify_clicked)
        login_layout.addWidget(btn_verify)

        layout.addWidget(login_card)

        # ── Cover card ──
        cover_card = SimpleCardWidget()
        cover_layout = QVBoxLayout(cover_card)
        cover_layout.setContentsMargins(12, 12, 12, 12)

        self.cover_label = BodyLabel('暂无封面')
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setMinimumHeight(200)

        img_path = os.path.join(DATA_DIR, '0035.png')
        if os.path.isfile(img_path):
            self.set_cover_image(img_path)

        cover_layout.addWidget(self.cover_label)
        layout.addWidget(cover_card, 1)

    def set_cover_image(self, path: str) -> None:
        try:
            image = Image.open(path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.thumbnail((300, 400), Image.LANCZOS)
            buf = BytesIO()
            image.save(buf, format='PNG')
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            self.cover_label.setPixmap(pixmap)
            self.cover_label.setMinimumHeight(0)
        except Exception:
            self.cover_label.setText('加载封面失败')
            self.cover_label.setPixmap(QPixmap())


# ── Settings Interface ─────────────────────────────────────────────────
class SettingsInterface(QFrame):
    def __init__(self, text: str, main=None):
        super().__init__(parent=main)
        self.main = main
        self._setup_ui()
        self.setObjectName(text.replace(' ', '-'))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── Save path ──
        path_card = SimpleCardWidget()
        path_layout = QHBoxLayout(path_card)
        path_layout.setContentsMargins(16, 12, 16, 12)
        path_layout.setSpacing(8)
        path_layout.addWidget(BodyLabel('保存地址:'))

        try:
            saved = open(os.path.join(DATA_DIR, 'video_file.txt'), 'r').read()
        except FileNotFoundError:
            saved = os.path.expanduser('~\\Downloads')

        self.folder_edit = LineEdit()
        self.folder_edit.setText(saved)
        self.folder_edit.setReadOnly(True)
        path_layout.addWidget(self.folder_edit, 1)

        btn_select = PushButton('📂 选择')
        btn_select.clicked.connect(self.main._on_select_folder)
        btn_open = PushButton('📁 打开')
        btn_open.clicked.connect(self.main._on_open_folder)
        path_layout.addWidget(btn_select)
        path_layout.addWidget(btn_open)
        layout.addWidget(path_card)

        # ── Open folder after download ──
        open_card = SimpleCardWidget()
        open_layout = QHBoxLayout(open_card)
        open_layout.setContentsMargins(16, 12, 16, 12)
        self.open_folder_switch = SwitchButton()
        # Restore from config
        cfg = load_config()
        self.open_folder_switch.setChecked(cfg.get('open_folder_after_download', False))
        self.open_folder_switch.checkedChanged.connect(
            lambda checked: save_config(
                {**load_config(), 'open_folder_after_download': checked}))
        open_layout.addWidget(BodyLabel('下载完成后打开所在文件夹'))
        open_layout.addStretch()
        open_layout.addWidget(self.open_folder_switch)
        layout.addWidget(open_card)

        # ── Theme ──
        theme_card = SimpleCardWidget()
        theme_layout = QHBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 12, 16, 12)
        theme_layout.addWidget(BodyLabel('深色模式'))
        self.theme_switch = SwitchButton()
        self.theme_switch.checkedChanged.connect(self.main._on_toggle_theme)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_switch)
        layout.addWidget(theme_card)

        # ── Clear cache ──
        btn_clear = PushButton('清除缓存')
        btn_clear.clicked.connect(self.main._on_clear_cache)
        layout.addWidget(btn_clear)

        layout.addStretch()


# ── Batch Download Interface ───────────────────────────────────────────
BATCH_MIN_INTERVAL = 5  # seconds — minimum to avoid IP ban


class BatchDownloadInterface(QFrame):
    def __init__(self, text: str, main=None):
        super().__init__(parent=main)
        self.main = main
        self._setup_ui()
        self.setObjectName(text.replace(' ', '-'))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── URL row ──
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        url_label = BodyLabel('视频地址:')
        url_label.setFixedWidth(70)
        self.url_edit = LineEdit()

        btn_fetch = PushButton('🔍 获取分P')
        btn_fetch.clicked.connect(self.main._on_batch_fetch_pages)
        url_row.addWidget(url_label)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(btn_fetch)
        layout.addLayout(url_row)

        # ── Quality + Mode ──
        opt_row = QHBoxLayout()
        opt_row.setSpacing(10)

        qual_card = SimpleCardWidget()
        ql = QHBoxLayout(qual_card)
        ql.setContentsMargins(12, 8, 12, 8)
        ql.setSpacing(6)
        ql.addWidget(BodyLabel('视频清晰度:'))
        self.quality_combo = ComboBox()
        self.quality_combo.addItems(['1080P60', '1080P高帧率', '1080P', '720P', '360P'])
        self.quality_combo.setCurrentIndex(0)
        ql.addWidget(self.quality_combo)
        opt_row.addWidget(qual_card)

        mode_card = SimpleCardWidget()
        ml = QHBoxLayout(mode_card)
        ml.setContentsMargins(12, 8, 12, 8)
        ml.setSpacing(6)
        ml.addWidget(BodyLabel('下载选项:'))
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(['视频+音频', '仅音频', '快速下载'])
        self.mode_combo.setCurrentIndex(0)
        ml.addWidget(self.mode_combo)
        opt_row.addWidget(mode_card)
        layout.addLayout(opt_row)

        # ── Page range + Interval (same row) ──
        batch_opt_row = QHBoxLayout()
        batch_opt_row.setSpacing(10)

        range_card = SimpleCardWidget()
        rl = QHBoxLayout(range_card)
        rl.setContentsMargins(12, 8, 12, 8)
        rl.setSpacing(8)
        rl.addWidget(BodyLabel('分P范围:'))
        self.range_start = SpinBox()
        self.range_start.setRange(1, 999)
        self.range_start.setValue(1)
        self.range_start.setFixedWidth(100)
        rl.addWidget(self.range_start)
        rl.addWidget(BodyLabel('—'))
        self.range_end = SpinBox()
        self.range_end.setRange(1, 999)
        self.range_end.setValue(1)
        self.range_end.setFixedWidth(100)
        rl.addWidget(self.range_end)
        rl.addStretch()
        batch_opt_row.addWidget(range_card)

        interval_card = SimpleCardWidget()
        ivl = QHBoxLayout(interval_card)
        ivl.setContentsMargins(12, 8, 12, 8)
        ivl.setSpacing(8)
        ivl.addWidget(BodyLabel('下载间隔(秒):'))
        self.interval_spin = SpinBox()
        self.interval_spin.setRange(BATCH_MIN_INTERVAL, 600)  # 5s ~ 10min
        self.interval_spin.setValue(BATCH_MIN_INTERVAL)
        self.interval_spin.setFixedWidth(100)
        ivl.addWidget(self.interval_spin)
        ivl.addWidget(BodyLabel('(最低 {}s，防封)'.format(BATCH_MIN_INTERVAL)))
        ivl.addStretch()
        batch_opt_row.addWidget(interval_card)

        layout.addLayout(batch_opt_row)

        # ── Status ──
        self.batch_status = status_label('就绪')
        layout.addWidget(self.batch_status)

        # ── Progress ──
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(22)
        layout.addWidget(self.progress_bar)

        # ── Log ──
        self.log_text = PlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        self.log_text.setPlaceholderText('操作日志...')
        self.log_text.setMinimumHeight(80)
        layout.addWidget(self.log_text, 1)

        # ── Start button ──
        btn_batch = PrimaryPushButton('▶ 开始批量下载')
        btn_batch.clicked.connect(self.main._on_batch_download_clicked)
        layout.addWidget(btn_batch)


# ── Clip / Trim Interface ──────────────────────────────────────────────
class ClipInterface(QFrame):
    def __init__(self, text: str, main=None):
        super().__init__(parent=main)
        self.main = main
        self._setup_ui()
        self.setObjectName(text.replace(' ', '-'))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── URL row ──
        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        url_label = BodyLabel('视频地址:')
        url_label.setFixedWidth(70)
        self.url_edit = LineEdit()

        btn_fetch = PushButton('🔍 获取分P')
        btn_fetch.clicked.connect(self.main._on_clip_fetch_pages)
        url_row.addWidget(url_label)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(btn_fetch)
        layout.addLayout(url_row)

        # ── Quality + page ──
        opt_row = QHBoxLayout()
        opt_row.setSpacing(10)

        qual_card = SimpleCardWidget()
        ql = QHBoxLayout(qual_card)
        ql.setContentsMargins(12, 8, 12, 8)
        ql.setSpacing(6)
        ql.addWidget(BodyLabel('视频清晰度:'))
        self.quality_combo = ComboBox()
        self.quality_combo.addItems(['1080P60', '1080P高帧率', '1080P', '720P', '360P'])
        self.quality_combo.setCurrentIndex(0)
        ql.addWidget(self.quality_combo)
        opt_row.addWidget(qual_card)

        page_card = SimpleCardWidget()
        pl = QHBoxLayout(page_card)
        pl.setContentsMargins(12, 8, 12, 8)
        pl.setSpacing(6)
        pl.addWidget(BodyLabel('分P选择:'))
        self.page_combo = ElidedComboBox()
        self.page_combo.addItems(['请先获取分P'])
        self.page_combo.setCurrentIndex(0)
        pl.addWidget(self.page_combo)
        opt_row.addWidget(page_card)

        dur_card = SimpleCardWidget()
        dl = QHBoxLayout(dur_card)
        dl.setContentsMargins(12, 8, 12, 8)
        dl.setSpacing(6)
        dl.addWidget(BodyLabel('视频时长:'))
        self.duration_label = BodyLabel('—')
        dl.addWidget(self.duration_label)
        dl.addStretch()
        opt_row.addWidget(dur_card)

        layout.addLayout(opt_row)

        # ── Time range (minutes + seconds) ──
        time_card = SimpleCardWidget()
        tl = QVBoxLayout(time_card)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setSpacing(8)

        # Start row
        start_row = QHBoxLayout()
        start_row.setSpacing(8)
        start_row.addWidget(BodyLabel('起始时间'))
        self.start_min_spin = SpinBox()
        self.start_min_spin.setRange(0, 99999)
        self.start_min_spin.setValue(0)
        self.start_min_spin.setFixedWidth(120)
        start_row.addWidget(self.start_min_spin)
        start_row.addWidget(BodyLabel('分'))
        self.start_sec_spin = SpinBox()
        self.start_sec_spin.setRange(0, 59)
        self.start_sec_spin.setValue(0)
        self.start_sec_spin.setFixedWidth(120)
        start_row.addWidget(self.start_sec_spin)
        start_row.addWidget(BodyLabel('秒'))
        start_row.addStretch()
        tl.addLayout(start_row)

        # End row
        end_row = QHBoxLayout()
        end_row.setSpacing(8)
        end_row.addWidget(BodyLabel('结束时间'))
        self.end_min_spin = SpinBox()
        self.end_min_spin.setRange(0, 99999)
        self.end_min_spin.setValue(0)
        self.end_min_spin.setFixedWidth(120)
        end_row.addWidget(self.end_min_spin)
        end_row.addWidget(BodyLabel('分'))
        self.end_sec_spin = SpinBox()
        self.end_sec_spin.setRange(0, 59)
        self.end_sec_spin.setValue(0)
        self.end_sec_spin.setFixedWidth(120)
        end_row.addWidget(self.end_sec_spin)
        end_row.addWidget(BodyLabel('秒'))
        end_row.addStretch()
        tl.addLayout(end_row)
        tl.addStretch()
        layout.addWidget(time_card)

        # ── Status ──
        self.clip_status = status_label('就绪')
        layout.addWidget(self.clip_status)

        # ── Progress + Log ──
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(22)
        layout.addWidget(self.progress_bar)

        self.log_text = PlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        self.log_text.setPlaceholderText('操作日志...')
        self.log_text.setMinimumHeight(80)
        layout.addWidget(self.log_text, 1)

        # ── Start button ──
        btn_clip = PrimaryPushButton('✂ 开始截取')
        btn_clip.clicked.connect(self.main._on_clip_clicked)
        layout.addWidget(btn_clip)


# ── Main Window ────────────────────────────────────────────────────────
class MainWindow(MSFluentWindow):
    """MSFluentWindow with 3 navigation pages: 下载 / 信息 / 设置."""

    update_status = pyqtSignal(str)
    update_info = pyqtSignal(str)
    log_message = pyqtSignal(str)
    update_progress = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self._is_dark = False  # start light; restored from config below
        self.page_list = []
        self.token = None
        self._dl_downloading = False
        self._batch_downloading = False
        self._clip_downloading = False
        self._clip_page_signal_connected = False

        # Create sub-interfaces
        self.dl = DownloadInterface('下载', self)
        self.batch = BatchDownloadInterface('批量下载', self)
        self.clip = ClipInterface('截取', self)
        self.info = InfoInterface('信息', self)
        self.settings = SettingsInterface('设置', self)

        # Navigation
        self.addSubInterface(self.dl, FIF.DOWNLOAD, '下载')
        self.addSubInterface(self.batch, FIF.SYNC, '批量')
        self.addSubInterface(self.clip, FIF.CUT, '截取')
        self.addSubInterface(self.info, FIF.INFO, '信息',
                             '', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings, FIF.SETTING, '设置',
                             '', NavigationItemPosition.BOTTOM)

        # Window properties
        self.setWindowTitle('BiliBili Video Download')
        ico_path = os.path.join(DATA_DIR, 'favicon.ico')
        if os.path.isfile(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        # Restore saved config（限制在屏幕内：旧配置可能保存过被长文本撑宽的尺寸）
        cfg = load_config()
        screen = QApplication.primaryScreen().availableGeometry()
        saved_w = max(820, min(int(cfg.get('window_width', 1100)),
                               screen.width() - 80))
        saved_h = max(560, min(int(cfg.get('window_height', 650)),
                               screen.height() - 80))
        self.setMinimumSize(820, 560)
        self.resize(saved_w, saved_h)
        self.move((screen.width() - saved_w) // 2, (screen.height() - saved_h) // 2)

        if cfg.get('dark_mode', False):
            self._is_dark = True
            setTheme(Theme.DARK)
            self.settings.theme_switch.setChecked(True)

        # Signal plumbing
        self.update_status.connect(self.dl.download_status.setText)
        self.update_info.connect(self.info.sidebar_info.setText)
        self.update_progress.connect(self._on_update_progress)
        self.log_message.connect(self._on_log_message)
        # Batch also listens to log/progress for its own widgets
        self.log_message.connect(self.batch.log_text.appendPlainText)
        self.update_progress.connect(self._on_batch_update_progress)
        # Auto-scroll batch log
        def _batch_scroll():
            sb = self.batch.log_text.verticalScrollBar()
            sb.setValue(sb.maximum())
        self.log_message.connect(_batch_scroll)
        # Clip signal plumbing
        self.log_message.connect(self.clip.log_text.appendPlainText)
        self.update_progress.connect(self._on_clip_update_progress)
        def _clip_scroll():
            sb = self.clip.log_text.verticalScrollBar()
            sb.setValue(sb.maximum())
        self.log_message.connect(_clip_scroll)

    # ── Inline slots ────────────────────────────────────────────────────

    def _on_log_message(self, msg: str) -> None:
        self.dl.log_text.appendPlainText(msg)
        sb = self.dl.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_update_progress(self, value: int, maximum: int) -> None:
        self.dl.progress_bar.setMaximum(maximum)
        self.dl.progress_bar.setValue(value)

    # ── Event handlers ──────────────────────────────────────────────────

    def _on_select_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, '选择保存目录')
        if path:
            self.settings.folder_edit.setText(path)
            with open(os.path.join(DATA_DIR, 'video_file.txt'), 'w') as f:
                f.write(path)

    def _on_open_folder(self) -> None:
        path = self.settings.folder_edit.text()
        if os.path.isdir(path):
            os.startfile(path)
        else:
            self.update_status.emit('所选保存路径不存在')

    def _on_paste_url(self) -> None:
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text:
            self.dl.url_edit.setText(clipboard_text)
            self.log_message.emit('[{}] 已从剪贴板粘贴 URL'.format(
                time.strftime('%H:%M:%S')))

    def _on_fetch_pages(self) -> None:
        user_input = self.dl.url_edit.text()
        vid, err = parse_vid(user_input)
        if err:
            self.dl.download_status.setText(err)
            return
        pages = down.get_page_list(vid)
        if not pages:
            self.dl.download_status.setText('获取分P信息失败，请检查地址')
            return
        self.page_list = pages
        for p in self.page_list:
            p['_input'] = vid
        self.dl.page_combo.clear()
        self.dl.page_combo.addItems(
            [elide_text("{}. {}".format(p['index'] + 1, p['part'])) for p in pages])
        self.dl.page_combo.setCurrentIndex(0)
        self.dl.download_status.setText('已获取分P列表，请选择分P后点击下载')
        self.log_message.emit('[{}] 已获取 {} 个分P'.format(
            time.strftime('%H:%M:%S'), len(pages)))

    def _on_download_clicked(self) -> None:
        if self._dl_downloading:
            self.dl.download_status.setText('已有下载任务进行中')
            return
        try:
            self._dl_downloading = True
            self._do_download()
        except RuntimeError as e:
            msg = str(e)
            self.dl.download_status.setText(msg)
            self.log_message.emit('[{}] 错误: {}'.format(
                time.strftime('%H:%M:%S'), msg))

    def _do_download(self) -> None:
        user_input = self.dl.url_edit.text()
        vid, err = parse_vid(user_input)
        if err:
            self.dl.download_status.setText(err)
            return

        definition = {'1080P60': '116', '1080P高帧率': '120', '1080P': '80', '720P': '64', '360P': '16'}
        def_idx = definition[self.dl.quality_combo.currentText()]
        down_obj = {'视频+音频': '0', '仅音频': '1', '快速下载': '2'}
        audio_id = down_obj[self.dl.mode_combo.currentText()]

        if not self.page_list:
            self.dl.download_status.setText('请先点击获取分P')
            return

        sel = self.dl.page_combo.currentIndex()
        if sel < 0 or sel >= len(self.page_list):
            self.dl.download_status.setText('分P选择无效')
            return
        page_index = self.page_list[sel]['index']

        try:
            video_url, video_title, total, audio_url, info = down.video_down(
                vid, def_idx, audio_id, page_index)
        except Exception as e:
            self.dl.download_status.setText(brief('获取视频地址失败: ' + str(e)))
            return

        if video_title == 'Warning_0':
            self.dl.download_status.setText(video_url)
            return

        # 实际清晰度和请求不一致时说明原因（B 站按账号权限降级）
        actual = (info or {}).get('quality')
        if actual:
            if audio_id == '1':
                self.log_message.emit('[{}] 仅下载音频（DASH 音频轨）'.format(
                    time.strftime('%H:%M:%S')))
            else:
                downgraded = info.get('quality_id') != info.get('requested')
                self.log_message.emit('[{}] 清晰度: 请求 {}{}'.format(
                    time.strftime('%H:%M:%S'), info.get('requested_name'),
                    ' → 实际 {}（B 站按账号权限降级）'.format(actual)
                    if downgraded else ''))

        suffix = video_title + '.mp4'
        if audio_id == '1':
            # DASH 音频轨是 m4a(AAC) 封装，别硬套 .mp3 后缀
            suffix = video_title + '.m4a'

        folder = self.settings.folder_edit.text()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            self.dl.download_status.setText(brief('保存路径不可用: ' + str(e)))
            return
        file_path = os.path.join(folder, suffix)

        if total == 0:
            self.dl.progress_bar.setMaximum(100)
            self.dl.progress_bar.setValue(0)
            self.dl.download_status.setText('准备下载...')
            td.Thread(target=self._download_worker,
                      args=(video_url, file_path, suffix, audio_url),
                      daemon=True).start()
        else:
            self._run_quick_down_task(total, file_path, video_url, audio_url)

    # ── 下载实现（durl 单文件 / DASH 音视频分离） ──────────────────────

    def _ffmpeg_exe(self) -> str:
        exe = shutil.which('ffmpeg')
        if exe:
            return exe
        for name in ('ffmpeg.exe', 'ffmpeg'):
            cand = os.path.join(APP_DIR, name)
            if os.path.isfile(cand):
                return cand
        return ''

    def _run_ffmpeg(self, cmd: list, timeout: int = 3600):
        """调用 ffmpeg（窗口化程序里不要弹出黑色控制台）"""
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(
                subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, **kwargs)

    def _download_dash(self, video_url: str, audio_url: str, file_path: str,
                       quick: bool = False) -> int:
        """
        1080P 及以上是 DASH：音视频分离，需下载两条流再交给 ffmpeg 合并。
        返回耗时秒数。
        """
        stem = re.sub(r'\.(mp4|mp3|m4a)$', '', file_path, flags=re.I)
        vpath, apath = stem + '.video.m4s', stem + '.audio.m4s'
        streams = [(video_url, vpath), (audio_url, apath)]
        try:
            start = time.time()
            if quick:
                sizes = []
                for url, _ in streams:
                    head = down.get_response(url, True)
                    sizes.append(int(head.headers.get('Content-Length') or 0))
                    head.close()
                if any(n <= 0 for n in sizes):
                    raise RuntimeError('取不到流大小，无法多线程下载')
                for (url, path), size in zip(streams, sizes):
                    qd.quick_down(size, path, url)
            else:
                responses = [down.get_response(u, True) for u, _ in streams]
                total = sum(int(r.headers.get('Content-Length') or 0)
                            for r in responses)
                written = 0
                for resp, (_, path) in zip(responses, streams):
                    with open(path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=1 << 18):
                            if chunk:
                                written += f.write(chunk)
                                self.update_progress.emit(written, max(total, 1))
            elapsed = int(time.time() - start)

            ffmpeg = self._ffmpeg_exe()
            if not ffmpeg:
                raise RuntimeError('未找到 ffmpeg，无法合并 1080P 音视频')
            cmd = [ffmpeg, '-y', '-loglevel', 'error',
                   '-i', vpath, '-i', apath,
                   '-c', 'copy', '-movflags', '+faststart', file_path]
            proc = self._run_ffmpeg(cmd)
            if proc.returncode != 0:
                raise RuntimeError('ffmpeg 合并失败: ' +
                                   (proc.stderr or '')[-300:])
            return elapsed
        finally:
            for path in (vpath, apath):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    def _download_worker(self, video_url: str, file_path: str, suffix: str,
                         audio_url: str = '') -> None:
        try:
            if audio_url:
                self.log_message.emit('[{}] 开始下载(DASH 音视频): {}'.format(
                    time.strftime('%H:%M:%S'), os.path.basename(file_path)))
                self.update_status.emit('下载中...')
                elapsed = self._download_dash(video_url, audio_url, file_path)
                msg = '下载完成,总用时: {:d}s'.format(elapsed)
                self.update_status.emit(msg)
                self.log_message.emit('[{}] {}'.format(
                    time.strftime('%H:%M:%S'), msg))
                self.update_progress.emit(0, 100)
                self._open_folder_if_enabled(file_path)
                return

            video = down.get_response(video_url, True)
            length = int(video.headers.get('Content-Length'))
            chunk_size = int(length * 0.02) + 10000

            self.log_message.emit('[{}] 开始下载: {}'.format(
                time.strftime('%H:%M:%S'), os.path.basename(file_path)))
            self.update_status.emit('下载中...')

            with open(file_path, 'wb') as f:
                start = time.time()
                written = 0
                for chunk in video.iter_content(chunk_size=chunk_size):
                    written += f.write(chunk)
                    self.update_progress.emit(written, length)

            elapsed = int(time.time() - start)
            msg = '下载完成,总用时: {:d}s'.format(elapsed)
            self.update_status.emit(msg)
            self.log_message.emit('[{}] {}'.format(
                time.strftime('%H:%M:%S'), msg))
            self.update_progress.emit(0, 100)
        except Exception as e:
            self.update_status.emit(brief('下载出错: ' + str(e)))
            self.log_message.emit('[{}] 下载错误: {}'.format(
                time.strftime('%H:%M:%S'), e))
        finally:
            self._dl_downloading = False

    def _run_quick_down_task(self, length: int, file_path: str,
                             video_url: str, audio_url: str = '') -> None:
        self.dl.download_status.setText('快速下载已启动，后台多线程下载中...')
        self.log_message.emit('[{}] 快速下载已启动（后台多线程）'.format(
            time.strftime('%H:%M:%S')))
        td.Thread(target=self._run_quick_down,
                  args=(length, file_path, video_url, audio_url),
                  daemon=True).start()

    def _run_quick_down(self, length: int, file_path: str,
                        video_url: str, audio_url: str = '') -> None:
        try:
            if audio_url:
                # DASH：两条流分别多线程下载后再合并
                elapsed = self._download_dash(video_url, audio_url,
                                              file_path, quick=True)
            else:
                elapsed = qd.quick_down(length, file_path, video_url)
            msg = '快速下载完成,总用时: {:d}s'.format(elapsed)
            self.update_status.emit(msg)
            self.log_message.emit('[{}] {}'.format(
                time.strftime('%H:%M:%S'), msg))
            self._open_folder_if_enabled(file_path)
        except Exception as e:
            self.update_status.emit(brief('快速下载出错: ' + str(e)))
            self.log_message.emit('[{}] 快速下载错误: {}'.format(
                time.strftime('%H:%M:%S'), e))
        finally:
            self._dl_downloading = False

    # ── Login handlers ──────────────────────────────────────────────────

    def _on_login_clicked(self) -> None:
        try:
            self.info.sidebar_info.setText('正在生成二维码...')
            self.token = verify.login()
            self.info.set_cover_image(os.path.join(DATA_DIR, 'my_blog.png'))
            self.info.sidebar_info.setText('请扫描二维码登录')
            td.Thread(target=self._qr_poll_thread, daemon=True).start()
        except Exception as e:
            self.info.sidebar_info.setText('登录失败: ' + str(e))
            self.log_message.emit('[{}] 登录出错: {}'.format(
                time.strftime('%H:%M:%S'), e))

    def _on_verify_clicked(self) -> None:
        cookie_path = os.path.join(DATA_DIR, 'your_cookie.txt')
        if os.path.isfile(cookie_path):
            self.info.sidebar_info.setText(verify.accept())
        else:
            self.info.sidebar_info.setText('未登录,请先登录')

    def _qr_poll_thread(self) -> None:
        cut = 1
        while cut < 121:
            time.sleep(1)
            if cut % 5 == 0:
                if verify.login_accept(self.token) == '已登录':
                    self.update_info.emit('已登录')
                    self.info.set_cover_image(os.path.join(
                        DATA_DIR, '0035.png'))
                    return
            cut += 1

    def _on_clear_cache(self) -> None:
        for name in ('my_blog.png', 'your_cookie.txt'):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                os.remove(path)
        self.info.sidebar_info.setText('已清除缓存')

    def _on_toggle_theme(self, checked: bool) -> None:
        setTheme(Theme.DARK if checked else Theme.LIGHT)
        self._is_dark = checked
        save_config({'window_width': self.width(), 'window_height': self.height(),
                     'dark_mode': checked})

    def _open_folder_if_enabled(self, path: str) -> None:
        """Download 完成后若开关打开则打开文件夹"""
        if load_config().get('open_folder_after_download', False):
            folder = os.path.dirname(path) if os.path.isfile(path) else path
            if os.path.isdir(folder):
                os.startfile(folder)

    # ── Persist window size when resized ────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Save size on resize (debounced by Qt's event coalescing)
        save_config({'window_width': self.width(), 'window_height': self.height(),
                     'dark_mode': self._is_dark})

    def closeEvent(self, event):
        save_config({'window_width': self.width(), 'window_height': self.height(),
                     'dark_mode': self._is_dark})
        super().closeEvent(event)

    # ── Batch download handlers ─────────────────────────────────────────

    def _on_batch_fetch_pages(self) -> None:
        """获取分P列表并更新批量页的范围 SpinBox"""
        user_input = self.batch.url_edit.text()
        vid, err = parse_vid(user_input)
        if err:
            self.batch.batch_status.setText(err)
            return
        pages = down.get_page_list(vid)
        if not pages:
            self.batch.batch_status.setText('获取分P信息失败，请检查地址')
            return
        self.batch_page_list = pages
        self.batch_vid = vid
        total = len(pages)
        self.batch.range_start.setRange(1, total)
        self.batch.range_end.setRange(1, total)
        self.batch.range_start.setValue(1)
        self.batch.range_end.setValue(total)
        self.batch.batch_status.setText('已获取 {} 个分P (1-{})'.format(total, total))
        self.log_message.emit('[{}] 批量: 已获取 {} 个分P'.format(
            time.strftime('%H:%M:%S'), total))

    def _on_batch_download_clicked(self) -> None:
        if self._batch_downloading:
            self.batch.batch_status.setText('已有批量任务进行中')
            return
        try:
            self._batch_downloading = True
            self._batch_start_download()
        except RuntimeError as e:
            msg = str(e)
            self.batch.batch_status.setText(msg)
            self.log_message.emit('[{}] 批量错误: {}'.format(
                time.strftime('%H:%M:%S'), msg))

    def _batch_start_download(self) -> None:
        """Validate inputs and launch batch download thread."""
        if not hasattr(self, 'batch_page_list') or not self.batch_page_list:
            self.batch.batch_status.setText('请先点击获取分P')
            return

        start = self.batch.range_start.value() - 1  # 0-based
        end = self.batch.range_end.value() - 1
        interval = self.batch.interval_spin.value()

        if start > end:
            self.batch.batch_status.setText('起始分P不能大于结束分P')
            return

        pages_to_download = self.batch_page_list[start:end + 1]
        quality = {'1080P60': '116', '1080P高帧率': '120', '1080P': '80', '720P': '64', '360P': '16'}
        def_idx = quality[self.batch.quality_combo.currentText()]
        down_mode = {'视频+音频': '0', '仅音频': '1', '快速下载': '2'}
        audio_id = down_mode[self.batch.mode_combo.currentText()]
        vid = self.batch_vid
        dest = self.settings.folder_edit.text()
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as e:
            self.batch.batch_status.setText(brief('保存路径不可用: ' + str(e)))
            return

        self.batch.progress_bar.setMaximum(len(pages_to_download))
        self.batch.progress_bar.setValue(0)
        self.batch.batch_status.setText('批量下载中...')

        td.Thread(target=self._batch_download_worker,
                  args=(vid, def_idx, audio_id, pages_to_download,
                        interval, dest),
                  daemon=True).start()

    def _batch_download_worker(self, vid: str, def_idx: str, audio_id: str,
                                pages: list, interval: int, dest: str) -> None:
        """Sequential batch download with interval between each."""
        total = len(pages)
        for i, page in enumerate(pages):
            page_index = page['index']
            part_name = page.get('part', '')
            current = i + 1

            self.log_message.emit('[{}] 批量 [{}/{}] 开始下载: {}'.format(
                time.strftime('%H:%M:%S'), current, total, part_name))
            self.update_status.emit('批量下载 [{}/{}]'.format(current, total))

            try:
                video_url, video_title, total_flag, audio_url, info = down.video_down(
                    vid, def_idx, audio_id, page_index)

                if video_title == 'Warning_0':
                    self.update_status.emit('分P {} 获取失败: {}'.format(current, video_url))
                    self.log_message.emit('[{}] 分P {} 跳过: {}'.format(
                        time.strftime('%H:%M:%S'), current, video_url))
                    continue

                suffix = video_title + '.mp4'
                if audio_id == '1':
                    suffix = video_title + '.m4a'

                file_path = os.path.join(dest, suffix)

                if audio_url:
                    # DASH：音视频分离，需要合并
                    elapsed = self._download_dash(
                        video_url, audio_url, file_path,
                        quick=(total_flag == 1))
                    msg = '分P {} 完成(音视频已合并),用时: {:d}s'.format(current, elapsed)
                elif total_flag == 0:
                    video = down.get_response(video_url, True)
                    length = int(video.headers.get('Content-Length'))
                    chunk_size = int(length * 0.02) + 10000
                    with open(file_path, 'wb') as f:
                        start_t = time.time()
                        for chunk in video.iter_content(chunk_size=chunk_size):
                            f.write(chunk)
                    elapsed = int(time.time() - start_t)
                    msg = '分P {} 完成,用时: {:d}s'.format(current, elapsed)
                else:
                    head = down.get_response(video_url, True)
                    size = int(head.headers.get('Content-Length') or 0)
                    head.close()
                    if size <= 0:
                        raise RuntimeError('取不到文件大小')
                    elapsed = qd.quick_down(size, file_path, video_url)
                    msg = '分P {} 快速下载完成,用时: {:d}s'.format(current, elapsed)

                self.update_status.emit(msg)
                self.log_message.emit('[{}] {}'.format(
                    time.strftime('%H:%M:%S'), msg))

            except Exception as e:
                self.log_message.emit('[{}] 分P {} 错误: {}'.format(
                    time.strftime('%H:%M:%S'), current, e))

            self.update_progress.emit(current, total)

            # Sleep between downloads (skip after last)
            if i < total - 1:
                self.log_message.emit('[{}] 等待 {:d}s...'.format(
                    time.strftime('%H:%M:%S'), interval))
                time.sleep(interval)

        self.update_status.emit('批量下载完成 ({}/{})'.format(total, total))
        self.batch.batch_status.setText('批量下载完成')
        self.log_message.emit('[{}] 批量下载全部完成'.format(time.strftime('%H:%M:%S')))
        self._batch_downloading = False

    def _on_batch_update_progress(self, value: int, maximum: int) -> None:
        """Update batch page's progress bar from signal."""
        self.batch.progress_bar.setMaximum(maximum)
        self.batch.progress_bar.setValue(value)

    # ── Clip / Trim handlers ────────────────────────────────────────────

    def _on_clip_fetch_pages(self) -> None:
        """获取分P，更新分P下拉 + 时长显示"""
        user_input = self.clip.url_edit.text()
        vid, err = parse_vid(user_input)
        if err:
            self.clip.clip_status.setText(err)
            return
        pages = down.get_page_list(vid)
        if not pages:
            self.clip.clip_status.setText('获取分P信息失败')
            return
        self.clip_page_list = pages
        self.clip_vid = vid
        self.clip.page_combo.clear()
        self.clip.page_combo.addItems(
            [elide_text("{}. {}".format(p['index'] + 1, p['part'])) for p in pages])
        self.clip.page_combo.setCurrentIndex(0)
        # Show duration for first page
        self._on_clip_page_changed(0)
        # Connect page change (只连一次，避免重复获取时信号叠加)
        if not self._clip_page_signal_connected:
            self.clip.page_combo.currentIndexChanged.connect(self._on_clip_page_changed)
            self._clip_page_signal_connected = True
        self.clip.clip_status.setText('已获取分P信息')
        self.log_message.emit('[{}] 截取: 已获取 {} 个分P'.format(
            time.strftime('%H:%M:%S'), len(pages)))

    def _on_clip_page_changed(self, idx: int) -> None:
        """切换分P时更新时长显示和结束时间的最大值"""
        if not hasattr(self, 'clip_page_list') or idx >= len(self.clip_page_list):
            return
        dur = self.clip_page_list[idx].get('duration', 0)
        m, s = divmod(dur, 60)
        self.clip.duration_label.setText('{:d} 分 {:d} 秒 ({:d}s)'.format(m, s, dur))
        self.clip.end_min_spin.setMaximum(m if dur > 0 else 99999)
        self.clip.end_min_spin.setValue(m)
        self.clip.end_sec_spin.setValue(s)

    def _on_clip_clicked(self) -> None:
        if self._clip_downloading:
            self.clip.clip_status.setText('已有截取任务进行中')
            return
        try:
            self._clip_downloading = True
            self._clip_start()
        except RuntimeError as e:
            msg = str(e)
            self.clip.clip_status.setText(msg)
            self.log_message.emit('[{}] 截取错误: {}'.format(
                time.strftime('%H:%M:%S'), msg))

    def _clip_start(self) -> None:
        """校验输入并启动截取线程"""
        if not hasattr(self, 'clip_page_list') or not self.clip_page_list:
            self.clip.clip_status.setText('请先获取分P')
            return

        # Check FFmpeg
        if not shutil.which('ffmpeg'):
            self.clip.clip_status.setText('未找到 FFmpeg，请安装后重试')
            self.log_message.emit('[{}] 错误: 未找到 FFmpeg，无法截取'.format(
                time.strftime('%H:%M:%S')))
            return

        sel = self.clip.page_combo.currentIndex()
        page = self.clip_page_list[sel]
        dur = page.get('duration', 0)
        start = self.clip.start_min_spin.value() * 60 + self.clip.start_sec_spin.value()
        end = self.clip.end_min_spin.value() * 60 + self.clip.end_sec_spin.value()

        if end <= start:
            self.clip.clip_status.setText('结束时间必须大于起始时间')
            return
        if end > dur > 0:
            end = dur

        quality = {'1080P60': '116', '1080P高帧率': '120', '1080P': '80', '720P': '64', '360P': '16'}
        def_idx = quality[self.clip.quality_combo.currentText()]
        vid = self.clip_vid
        dest = self.settings.folder_edit.text()

        self.clip.progress_bar.setMaximum(100)
        self.clip.progress_bar.setValue(0)
        self.clip.clip_status.setText('正在获取视频...')

        td.Thread(target=self._clip_download_and_trim,
                  args=(vid, def_idx, page, start, end, dest),
                  daemon=True).start()

    def _clip_download_and_trim(self, vid: str, def_idx: str,
                                 page: dict, start: int, end: int,
                                 dest: str) -> None:
        """下载完整视频 → FFmpeg 裁剪 → 清理临时文件"""
        temp_path = os.path.join(DATA_DIR, '_clip_temp.mp4')
        try:
            # ── Step 1: download ──
            video_url, video_title, total_flag, audio_url, info = down.video_down(
                vid, def_idx, '0', page['index'])
            if video_title == 'Warning_0':
                self.clip.clip_status.setText('获取视频失败: ' + video_url)
                return

            suffix = video_title + '_clip_{}s-{}s.mp4'.format(start, end)
            output_path = os.path.join(dest, suffix)

            self.log_message.emit('[{}] 正在下载完整视频...'.format(
                time.strftime('%H:%M:%S')))
            self.clip.clip_status.setText('下载中 (1/2)...')
            self.update_progress.emit(0, 100)

            if audio_url:
                # DASH：先合并音视频到临时文件
                self._download_dash(video_url, audio_url, temp_path)
            else:
                video = down.get_response(video_url, True)
                length = int(video.headers.get('Content-Length'))
                chunk_size = int(length * 0.02) + 10000
                with open(temp_path, 'wb') as f:
                    start_t = time.time()
                    written = 0
                    for chunk in video.iter_content(chunk_size=chunk_size):
                        written += f.write(chunk)
                        self.update_progress.emit(
                            int(written * 100 / length), 100)

            # ── Step 2: FFmpeg trim ──
            self.log_message.emit('[{}] FFmpeg 裁剪中 ({:d}s → {:d}s)...'.format(
                time.strftime('%H:%M:%S'), start, end))
            self.clip.clip_status.setText('裁剪中 (2/2)...')
            self.update_progress.emit(50, 100)

            ffmpeg_cmd = [
                self._ffmpeg_exe() or 'ffmpeg', '-y',
                '-ss', str(start),
                '-i', temp_path,
                '-to', str(end - start),
                '-c', 'copy',
                output_path
            ]
            result = self._run_ffmpeg(ffmpeg_cmd, timeout=1800)
            if result.returncode != 0:
                raise RuntimeError('FFmpeg 失败: ' + result.stderr[-300:])

            # ── Cleanup ──
            if os.path.isfile(temp_path):
                os.remove(temp_path)

            elapsed = int(time.time() - start_t)
            msg = '截取完成: {} ({:d}s)'.format(os.path.basename(output_path), elapsed)
            self.clip.clip_status.setText(msg)
            self.log_message.emit('[{}] {}'.format(
                time.strftime('%H:%M:%S'), msg))
            self._open_folder_if_enabled(output_path)
            self.update_progress.emit(100, 100)

        except Exception as e:
            # Cleanup on error
            if os.path.isfile(temp_path):
                os.remove(temp_path)
            self.clip.clip_status.setText('截取出错: ' + str(e))
            self.log_message.emit('[{}] 截取错误: {}'.format(
                time.strftime('%H:%M:%S'), e))
        finally:
            self._clip_downloading = False

    def _on_clip_update_progress(self, value: int, maximum: int) -> None:
        self.clip.progress_bar.setMaximum(maximum)
        self.clip.progress_bar.setValue(value)


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not is_process_running('BilibiliVideoDown.exe'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        app.exec_()
