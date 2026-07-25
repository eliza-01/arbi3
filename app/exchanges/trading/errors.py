class ExchangeTradingError(Exception):
    """Base error for authenticated exchange operations."""


class ExchangeDisabledError(ExchangeTradingError):
    pass


class ExchangeNotConfiguredError(ExchangeTradingError):
    pass


class ExchangeRequestError(ExchangeTradingError):
    pass
