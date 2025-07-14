import asyncio
import pandas as pd
from crypto import CryptoExchange_WS

# Hàm tính RSI không thay đổi
async def calculate_rsi_wilder(closes, period=14):
    """Tính RSI theo phương pháp Wilder (giống TradingView)"""
    series = pd.Series(closes, dtype=float)
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Tránh chia cho 0
    if avg_loss.iloc[-1] == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

async def monitor_resampled_rsi(ws, symbol, custom_timeframe="15s"):
    """
    Giám sát RSI bằng cách lấy dữ liệu giao dịch (trades) và tự tổng hợp (resample)
    thành các khung thời gian tùy chỉnh.
    """
    print(f"Bắt đầu theo dõi {symbol} trên khung tùy chỉnh {custom_timeframe}...")
    
    all_trades = []
    last_candle_timestamp = None

    while True:
        try:
            # Bước 1: Lấy dữ liệu giao dịch real-time
            new_trades = await ws.watch_trades(symbol)
            if not new_trades:
                continue
            
            all_trades.extend(new_trades)

            # Bước 2: Chuyển đổi và tổng hợp thành nến (OHLCV)
            df = pd.DataFrame(all_trades)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('datetime')

            # Tổng hợp (resample)
            ohlc_df = df['price'].resample(custom_timeframe).ohlc()
            
            # Lấp đầy các khoảng trống: nếu 1 giây không có giao dịch, giá của nó sẽ bằng giá của giây trước đó
            ohlc_df.ffill(inplace=True)

            # Bỏ dòng cuối cùng vì đó là nến đang chạy, chưa đóng
            closed_candles = ohlc_df.iloc[:-1]

            if closed_candles.empty:
                continue

            # Bước 3: Kiểm tra xem có nến mới vừa đóng không
            current_candle_timestamp = closed_candles.index[-1]
            if last_candle_timestamp is None or current_candle_timestamp > last_candle_timestamp:
                
                # Cập nhật timestamp của nến mới nhất
                last_candle_timestamp = current_candle_timestamp
                
                # Lấy danh sách giá đóng cửa
                closes = closed_candles['close'].dropna().tolist()

                if len(closes) > 14:
                    rsi = await calculate_rsi_wilder(closes)
                    print(f"--- NẾN {custom_timeframe} ĐÃ ĐÓNG ---")
                    # Chuyển đổi timestamp sang múi giờ Việt Nam (fix lỗi tz-naive)
                    local_timestamp = last_candle_timestamp.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
                    print(f"{symbol}: RSI-14 = {rsi:.2f} | Thời gian: {local_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            # Dọn dẹp bớt dữ liệu cũ để tránh tràn bộ nhớ
            cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(minutes=30)
            all_trades = [t for t in all_trades if t['timestamp'] > cutoff.timestamp() * 1000]

        except Exception as e:
            print(f"Lỗi theo dõi {symbol}: {str(e)}")
            await asyncio.sleep(5)

async def main():
    # Nhập token và sàn
    tokens_input = input("Nhập danh sách token (vd: BTC/USDT,ETH/USDT): ")
    tokens = [t.strip() for t in tokens_input.split(",")]
    
    exchange_name = input("Nhập tên sàn (vd: binanceusdm, bybit): ")
    timeframe = input("Khung thời gian (vd: 1s, 15s, 30s, 1m): ") or "15s"
    
    # Khởi tạo WebSocket client
    ws = CryptoExchange_WS()
    ws.setupEchange(exchange_name=exchange_name)
    
    # Kiểm tra token hợp lệ
    markets = await ws.load_markets()
    valid_tokens = []
    
    for token in tokens:
        if token in markets:
            valid_tokens.append(token)
        else:
            print(f"Token {token} không tìm thấy trên sàn {exchange_name}")
    
    # Chạy nhiều task monitor cùng lúc
    tasks = [monitor_resampled_rsi(ws, token, timeframe) for token in valid_tokens]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("Đang dừng chương trình...")
    finally:
        if ws.exchange:
            await ws.close()

if __name__ == "__main__":
    # Cài đặt event loop
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        # Bỏ qua lỗi trên Windows
        pass
    
    asyncio.run(main())