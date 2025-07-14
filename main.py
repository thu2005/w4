import asyncio
from manager import ExchangeManager
import pandas as pd
import numpy as np
from crypto import CryptoExchange_WS

async def calculate_rsi_wilder(closes, period=14):
    """Tính RSI theo phương pháp Wilder (giống TradingView)"""
    delta = pd.Series(closes).diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

async def monitor_token_rsi(ws, symbol, timeframe="1m"):
    """Giám sát RSI real-time cho một token"""
    print(f"Bắt đầu theo dõi {symbol} trên khung {timeframe}...")
    
    # Bước 1: Lấy dữ liệu lịch sử để "mồi" cho việc tính toán
    try:
        # Lấy nhiều nến hơn (tối đa 1000) để tăng độ chính xác ban đầu
        all_candles = await ws.fetch_ohlcv(symbol, timeframe=timeframe, limit=1000)
        if not all_candles:
            print(f"Không có dữ liệu lịch sử cho {symbol}, không thể bắt đầu.")
            return
        # Chỉ lấy giá đóng cửa
        closes = [candle[4] for candle in all_candles]
        print(f"Đã lấy {len(closes)} nến lịch sử cho {symbol}. Bắt đầu theo dõi real-time.")
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu lịch sử cho {symbol}: {e}")
        return

    # Bước 2: Theo dõi real-time
    while True:
        try:
            # Lấy nến mới nhất qua websocket
            new_candles = await ws.watch_ohlcv(symbol, timeframe=timeframe)
            
            for candle in new_candles:
                is_new_candle_formed = candle[0] > all_candles[-1][0]

                # CHỈ IN KHI NẾN CŨ ĐÃ ĐÓNG VÀ NẾN MỚI HÌNH THÀNH
                if is_new_candle_formed:
                    # Nến cũ (all_candles[-1]) đã đóng. Tính và in RSI của nó.
                    # Dữ liệu `closes` hiện tại đang chứa giá đóng cửa cuối cùng của nến vừa rồi.
                    if len(closes) > 14:
                        rsi = await calculate_rsi_wilder(closes)
                        print(f"--- NẾN {timeframe} ĐÃ ĐÓNG ---")
                        print(f"{symbol}: RSI-14 = {rsi:.2f} | Thời gian: {pd.to_datetime(all_candles[-1][0], unit='ms')}")
                    
                    # Bây giờ mới thêm nến mới vào danh sách
                    all_candles.append(candle)
                    closes.append(candle[4])
                    # Giữ danh sách ở kích thước hợp lý, bỏ nến cũ nhất
                    if len(closes) > 500:
                        closes.pop(0)
                        all_candles.pop(0)
                
                # Nếu chỉ là cập nhật giá của nến hiện tại, thì chỉ cập nhật, không in
                elif candle[0] == all_candles[-1][0]:
                    all_candles[-1] = candle
                    closes[-1] = candle[4]

        except Exception as e:
            print(f"Lỗi theo dõi {symbol}: {str(e)}")
            await asyncio.sleep(5)  # Đợi và thử lại

async def main():
    # Nhập token và sàn
    tokens_input = input("Nhập danh sách token (cách nhau bởi dấu phẩy, vd: BTC/USDT,ETH/USDT): ")
    tokens = [t.strip() for t in tokens_input.split(",")]
    
    exchange_name = input("Nhập tên sàn (vd: binanceusdm, bybit): ")
    timeframe = input("Khung thời gian (mặc định 1m): ") or "1m"
    
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
    tasks = [monitor_token_rsi(ws, token, timeframe) for token in valid_tokens]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("Đang dừng chương trình...")
    finally:
        if ws.exchange:
            await ws.close()  # Đóng kết nối websocket khi kết thúc

if __name__ == "__main__":
    # Cài đặt event loop
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsSelectorEventLoopPolicy':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())