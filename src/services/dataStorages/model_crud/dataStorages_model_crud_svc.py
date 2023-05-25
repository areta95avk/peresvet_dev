import sys
import copy

sys.path.append(".")

from dataStorages_model_crud_settings import DataStoragesModelCRUDSettings
from src.common import model_crud_svc
from src.common import hierarchy

class DataStoragesModelCRUD(model_crud_svc.ModelCRUDSvc):
    """Сервис работы с хранилищами данных в иерархии.

    Подписывается на очередь ``dataStorages_api_crud`` обменника ``dataStorages_api_crud``,
    в которую публикует сообщения сервис ``dataStorages_api_crud`` (все имена
    указываются в переменных окружения).

    Формат ожидаемых сообщений

    """

    def __init__(self, settings: DataStoragesModelCRUDSettings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)

    async def _reading(self, mes: dict) -> dict:
        pass

    async def _creating(self, mes: dict, new_id: str) -> None:
        pass

settings = DataStoragesModelCRUDSettings()

app = DataStoragesModelCRUD(settings=settings, title="DataStoragesModelCRUD")
