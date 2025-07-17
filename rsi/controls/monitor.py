
from PySide6.QtCore import QThread, Signal, QObject
from .indicator import RSIIndicator
import time

class RSIMonitorWorker(QObject):
    rsi_updated = Signal(float)
    error = Signal(str)

    def __init__(self, ws, symbol, interval):
        super().__init__()
        self.ws = ws
        self.symbol = symbol
        self.interval = interval
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        print(f"[RSIMonitor] Bắt đầu monitor (QThread): {self.symbol} | Interval: {self.interval}")
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            all_candles = loop.run_until_complete(self.ws.fetch_ohlcv(self.symbol, timeframe=self.interval, limit=100))
            closes = [c[4] for c in all_candles]
            print(f"[RSIMonitor] Đã lấy {len(closes)} nến lịch sử cho {self.symbol}")
        except Exception as e:
            print(f"[RSIMonitor] Lỗi khi fetch_ohlcv: {e}")
            self.error.emit(str(e))
            return
        while self._running:
            try:
                new_candles = loop.run_until_complete(self.ws.watch_ohlcv(self.symbol, timeframe=self.interval))
                print(f"[RSIMonitor] Nhận {len(new_candles)} nến mới cho {self.symbol}")
                for candle in new_candles:
                    is_new_candle_formed = candle[0] > all_candles[-1][0]
                    if is_new_candle_formed:
                        closes.append(candle[4])
                        if len(closes) > 14:
                            rsi = RSIIndicator(14).calculate(closes)
                            self.rsi_updated.emit(rsi)
                            print(f"[RSIMonitor] RSI cập nhật: {rsi} | Token: {self.symbol} | Interval: {self.interval}")
                        all_candles.append(candle)
                        if len(closes) > 500:
                            closes.pop(0)
                            all_candles.pop(0)
                    elif candle[0] == all_candles[-1][0]:
                        all_candles[-1] = candle
                        closes[-1] = candle[4]
                time.sleep(1)
            except Exception as e:
                print(f"[RSIMonitor] Lỗi khi watch_ohlcv: {e}")
                self.error.emit(str(e))
                time.sleep(5)
        if hasattr(self.ws, 'close'):
            loop.run_until_complete(self.ws.close())

class RSIMonitor:
    def __init__(self, ws, symbol, interval, on_rsi_update=None):
        self.worker = RSIMonitorWorker(ws, symbol, interval)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.rsi_updated.connect(on_rsi_update)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.on_rsi_update = on_rsi_update

    def start(self):
        self.thread.start()

    def stop(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()

    def handle_error(self, msg):
        print(f"[RSIMonitor] Error: {msg}")
        if self.on_rsi_update:
            self.on_rsi_update('--')
