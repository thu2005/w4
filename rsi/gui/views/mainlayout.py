from typing import TYPE_CHECKING
from .mainwidget_ui import Ui_MainWidget
from rsi.gui.components import CircularProgress
from rsi.gui.qfluentwidgets.common import FluentStyleSheet
from PySide6.QtWidgets import QFrame, QWidget
from PySide6.QtCore import Signal, Qt, QEvent, QTime
from rsi.gui.qfluentwidgets.common.icon import *
from rsi.appmanager.setting import AppConfig
from rsi.controls.main import calculate_rsi_wilder
from rsi.controls.manager import ExchangeManager
import asyncio
from rsi.controls.monitor import RSIMonitor

if TYPE_CHECKING:
    from .fluentwindow import WindowBase


class MainWidget(QWidget, Ui_MainWidget):
    mouse_clicked_signal = Signal(QEvent)

    def __init__(
        self, parent, tabItem, name, current_ex, current_symbol, curent_interval
    ):
        super().__init__(parent)
        self._parent: WindowBase = parent
        self.setObjectName(name)
        self.setupUi(self)

        self.maxExtend = 250
        self.tabItem = tabItem

        self.current_ex = current_ex
        self.current_symbol = current_symbol
        self.current_interval = curent_interval  # Lưu interval hiện tại

        self.rsi_monitor = None
        self.start_rsi_monitor(current_symbol, curent_interval, current_ex)


        self.chartbox_splitter.setup_chart(
        self, current_ex, current_symbol, curent_interval
        )

        self.chartbox_splitter.setup_chart(
            self, current_ex, current_symbol, curent_interval
        )

        # KHÔNG gọi asyncio.create_task ở đây để tránh lỗi event loop
        # Nếu muốn cập nhật RSI ban đầu, có thể gọi hàm sync lấy dữ liệu hoặc cập nhật khi có event loop
        # self.set_rsi_value('--')  # Hiển thị mặc định khi khởi tạo

        # Keep only essential chart signals
        self.chartbox_splitter.chart.sig_change_tab_infor.connect(
            self.change_tab_infor, Qt.ConnectionType.AutoConnection
        )
        self.chartbox_splitter.chart.mouse_clicked_on_chart.connect(
            self.mouse_clicked_signal
        )

        self.tool_name: str = None

        "signal from TopBar--------start"
        self.topbar.sig_change_symbol.connect(
            self.on_symbol_changed,
            Qt.ConnectionType.AutoConnection,
        )
        self.topbar.sig_change_inteval.connect(
            self.on_interval_changed,
            Qt.ConnectionType.AutoConnection,
        )
        "signal from TopBar-------end"


        "khởi tạo indicator menu, symbol menu trước. đang test"
        self.topbar.setup_symbol_menu()

        # Remove bottom interface for minimal RSI app
        # self.TabInterface = BottomInterface(self)
        # self.layout_bottom.addWidget(self.TabInterface)
        # self.splitter.setSizes([600, 60])

        self.press_time = None
        self.release_time = None

    def start_rsi_monitor(self, symbol, interval, exchange_id):
        # Dừng monitor cũ nếu có
        if self.rsi_monitor:
            self.rsi_monitor.stop()
        manager = ExchangeManager()
        ws_history = manager.set_ws_exchange(exchange_id, "chart1", symbol, interval, apikey="", secretkey="")
        ws_monitor = manager.set_ws_exchange(exchange_id, "chart1", symbol, interval, apikey="", secretkey="")

        # Worker chỉ fetch 1500 nến, tính RSI và emit về UI
        from rsi.appmanager.worker.qthreads import FastWorker
        def fetch_and_calc_rsi(setdata=None):
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                candles = loop.run_until_complete(ws_history.fetch_ohlcv(symbol, timeframe=interval, limit=1500))
                closes = [c[4] for c in candles]
                from rsi.controls.indicator import RSIIndicator
                rsi = RSIIndicator(14).calculate(closes)
                if setdata:
                    setdata.emit(rsi)
                loop.close()
            except Exception as e:
                print(f"[UI] Lỗi lấy RSI lịch sử: {e}")
                if setdata:
                    setdata.emit('--')

        self.rsi_worker = FastWorker(self, fetch_and_calc_rsi)
        self.rsi_worker.signals.setdata.connect(self.set_rsi_value)
        def start_monitor_after_worker():
            # Sau khi hiển thị RSI đầu tiên, khởi động monitor real-time
            self.rsi_monitor = RSIMonitor(ws_monitor, symbol, interval, on_rsi_update=self.set_rsi_value)
            self.rsi_monitor.start()
        # Worker không có finished signal, nên dùng thread join trong một hàm phụ hoặc callback setdata lần đầu
        # Đảm bảo chỉ start monitor sau khi setdata đầu tiên
        def set_rsi_and_start_monitor(value):
            self.set_rsi_value(value)
            start_monitor_after_worker()
            # Ngắt kết nối để không gọi lại nhiều lần
            self.rsi_worker.signals.setdata.disconnect()
        self.rsi_worker.signals.setdata.connect(set_rsi_and_start_monitor)
        self.rsi_worker.start_thread()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Progress disabled for RSI monitor
        pass

    def change_tab_infor(self, data):
        symbol = data[0]
        interval = data[1]
        symbol_icon = get_symbol_icon(symbol)
        symbol_icon_path = CryptoIcon.crypto_url(symbol_icon)
        text = f"{symbol} {interval}"
        self.tabItem.setIcon(symbol_icon_path)
        self.tabItem.setText(text)

        # self.maxExtend = width

    def mousePressEvent(self, ev: QEvent):
        if Qt.MouseButton.LeftButton:
            self.press_time = QTime.currentTime()
            super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QEvent):
        self.is_mouse_pressed = False
        self.release_time = QTime.currentTime()
        if self.press_time:
            elapsed_time = self.press_time.msecsTo(self.release_time)
            if elapsed_time < 200:
                self.mouse_clicked_signal.emit(ev)
        super().mouseReleaseEvent(ev)

    def set_rsi_value(self, value):
        import datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[UI] {now} | Token: {self.current_symbol} | Interval: {self.current_interval} | RSI cập nhật: {value}")
        try:
            val = float(value)
            self.rsiLabel.setText(f"RSI: {val:.2f}")
        except Exception:
            self.rsiLabel.setText(f"RSI: {value}")

    async def update_rsi(self, symbol, interval, exchange_id):
        manager = ExchangeManager()
        ws = manager.set_ws_exchange(exchange_id, "chart1", symbol, interval, apikey="", secretkey="")
        candles = await ws.fetch_ohlcv(symbol, timeframe=interval, limit=100)
        closes = [c[4] for c in candles]
        rsi = await calculate_rsi_wilder(closes, period=14)
        self.set_rsi_value(rsi)
        # Đóng kết nối exchange để tránh lỗi unclosed client session
        if hasattr(ws, 'close'):
            await ws.close()


    def on_symbol_changed(self, args):
        # args: ("change_symbol", symbol, exchange_id, exchange_name, symbol_icon_path, echange_icon_path, _mode)
        symbol = args[1]
        exchange_id = args[2]
        # Luôn dùng self.current_interval để đảm bảo interval hợp lệ
        self.start_rsi_monitor(symbol, self.current_interval, exchange_id)

    def on_interval_changed(self, args):
        # args: ("change_interval", interval)
        interval = args[1]
        self.current_interval = interval  # Cập nhật interval hiện tại
        symbol = self.topbar.get_current_symbol()
        exchange_id = self.topbar.get_current_exchange()
        self.start_rsi_monitor(symbol, interval, exchange_id)
