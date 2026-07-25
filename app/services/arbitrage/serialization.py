from app.db.models.arbitrage_trade import ArbitrageTrade
from app.services.instruments.catalog import InstrumentCatalog
from app.services.spreads.pairs import pair_row_key


def exchange_code_by_id(asset, exchange_id: int) -> str:
    for code, current_id in asset.exchange_ids.items():
        if current_id == exchange_id:
            return code
    return "unknown"


def serialize_trade(trade: ArbitrageTrade, catalog: InstrumentCatalog) -> dict:
    asset = catalog.get(trade.asset_id)
    if asset is None:
        display_symbol = f"asset:{trade.asset_id}"
        exchange_a = str(trade.exchange_a_id)
        exchange_b = str(trade.exchange_b_id)
        buy_exchange = str(trade.buy_exchange_id)
        sell_exchange = str(trade.sell_exchange_id)
    else:
        display_symbol = f"{asset.base_asset}/{asset.quote_asset}"
        exchange_a = exchange_code_by_id(asset, trade.exchange_a_id)
        exchange_b = exchange_code_by_id(asset, trade.exchange_b_id)
        buy_exchange = exchange_code_by_id(asset, trade.buy_exchange_id)
        sell_exchange = exchange_code_by_id(asset, trade.sell_exchange_id)
    return {
        "id": trade.id,
        "row_key": pair_row_key(trade.asset_id, exchange_a, exchange_b),
        "asset_id": trade.asset_id,
        "display_symbol": display_symbol,
        "exchange_a": exchange_a,
        "exchange_b": exchange_b,
        "buy_exchange": buy_exchange,
        "sell_exchange": sell_exchange,
        "buy_symbol": trade.buy_symbol,
        "sell_symbol": trade.sell_symbol,
        "status": trade.status,
        "position_usdt": float(trade.position_usdt),
        "leverage": trade.leverage,
        "rounding": trade.rounding,
        "insurance_seconds": float(trade.insurance_seconds),
        "buy_quantity": float(trade.buy_quantity) if trade.buy_quantity is not None else None,
        "sell_quantity": float(trade.sell_quantity) if trade.sell_quantity is not None else None,
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "error_message": trade.error_message,
        "created_at": trade.created_at.isoformat(),
        "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
    }
