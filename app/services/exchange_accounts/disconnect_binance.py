from app.local_settings.store import LocalSettingsStore


class DisconnectBinanceService:
    def __init__(self, settings_store: LocalSettingsStore) -> None:
        self._settings_store = settings_store

    def execute(self) -> dict:
        settings = self._settings_store.update({"binance": {"enabled": False}})
        return {
            **settings.to_dict(hide_secrets=True)["binance"],
            "state": "disabled",
            "message": "Подключение отключено",
        }
