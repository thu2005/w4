from indicator import CryptoExchange_WS

class ExchangeManager:
    def __init__(self):
        self.map_chart_exchange = {}

    def set_ws_exchange(self, id_exchange, chart_id, symbol, interval, apikey, secretkey):
        ws = CryptoExchange_WS().setupEchange(
            apikey=apikey, secretkey=secretkey, exchange_name=id_exchange
        )
        key = f"ws-{chart_id}-{symbol}-{interval}"
        if key not in self.map_chart_exchange:
            self.map_chart_exchange[key] = {f"ws-{id_exchange}": ws}
        else:
            self.map_chart_exchange[key][f"ws-{id_exchange}"] = ws
        return ws

    def get_ws_exchange(self, id_exchange, chart_id, symbol, interval):
        key = f"ws-{chart_id}-{symbol}-{interval}"
        chart = self.map_chart_exchange.get(key)
        if chart:
            return chart.get(f"ws-{id_exchange}")
        return None

    def clear(self):
        self.map_chart_exchange.clear()