from src.common.svc_settings import SvcSettings

class AlertsAppAPISettings(SvcSettings):

    #: имя сервиса
    svc_name: str = "alerts_app_api"
    #: версия API
    api_version: str = "/v1"

    