API_BASE_URL = "https://fapi.binance.com"
RECV_WINDOW = 5000

PING = "/fapi/v1/ping"
SERVER_TIME = "/fapi/v1/time"
EXCHANGE_INFO = "/fapi/v1/exchangeInfo"
BOOK_TICKER = "/fapi/v1/ticker/bookTicker"
ACCOUNT_BALANCE = "/fapi/v3/balance"
POSITION_RISK = "/fapi/v3/positionRisk"
POSITION_MODE = "/fapi/v1/positionSide/dual"
CHANGE_LEVERAGE = "/fapi/v1/leverage"
NEW_ORDER = "/fapi/v1/order"

DEFAULT_HEADERS = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
    "user-agent": "Arbi3/0.1",
}
