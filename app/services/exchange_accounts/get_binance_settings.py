from app.local_settings.store import LocalSettingsStore


class GetBinanceSettingsService:
    def __init__(self, settings_store: LocalSettingsStore) -> None:
        self._settings_store = settings_store

    def execute(self) -> dict:
        return self._settings_store.load().to_dict(hide_secrets=True)["binance"]
