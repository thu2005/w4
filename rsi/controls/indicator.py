from enum import Enum
from .crypto import CryptoExchange, CryptoExchange_WS
import pandas as pd


import pandas as pd

def rma(series, length):
    return series.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

class RSIIndicator:
    def __init__(self, period=14, mamode='rma', drift=1, offset=0, scalar=100):
        self.period = period
        self.mamode = mamode
        self.drift = drift
        self.offset = offset
        self.scalar = scalar

    def calculate(self, closes):
        if len(closes) < self.period:
            return None
        close = pd.Series(closes)
        diff = close.diff(self.drift)
        positive = diff.copy()
        negative = diff.copy()
        positive[positive < 0] = 0
        negative[negative > 0] = 0

        if self.mamode == 'rma':
            pos_avg = rma(positive, self.period)
            neg_avg = rma(negative, self.period)
        elif self.mamode == 'ema':
            pos_avg = positive.ewm(span=self.period, min_periods=self.period, adjust=False).mean()
            neg_avg = negative.ewm(span=self.period, min_periods=self.period, adjust=False).mean()
        elif self.mamode == 'sma':
            pos_avg = positive.rolling(window=self.period, min_periods=self.period).mean()
            neg_avg = negative.rolling(window=self.period, min_periods=self.period).mean()
        else:
            pos_avg = rma(positive, self.period)
            neg_avg = rma(negative, self.period)

        rsi = self.scalar * pos_avg / (pos_avg + abs(neg_avg))
        if self.offset != 0:
            rsi = rsi.shift(self.offset)
        return float(rsi.iloc[-1]) if not rsi.empty else None