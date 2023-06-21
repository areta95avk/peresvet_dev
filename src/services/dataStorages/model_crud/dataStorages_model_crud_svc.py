import sys
import copy
import json
from ldap.dn import str2dn, dn2str

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

    async def _further_read(self, mes: dict, search_result: dict) -> dict:
        res = {"data": []}
        for ds in search_result["data"]:
            ds_id = ds["id"]
            new_ds = copy.deepcopy(ds)
            if mes["getLinkedTags"]:
                new_ds["linkedTags"] = []
                async for item in self._hierarchy.search(
                    {
                        "base": ds_id,
                        "filter": {
                            "objectClass": ["prsDatastorageTagData"]
                        },
                        "attributes": ["cn", "prsStore"]
                    }
                ):
                    if item[0]:
                        new_ds["linkedTags"].append(
                            {
                                "id": item[0],
                                "attributes": {
                                    "prsStore": item[2]["prsStore"][0]
                                }
                            }
                        )

            if mes["getLinkedAlerts"]:
                new_ds["linkedAlerts"] = []
                async for item in self._hierarchy.search(
                    {
                        "base": ds_id,
                        "filter": {
                            "objectClass": ["prsDatastorageAlertData"]
                        },
                        "attributes": ["cn", "prsStore"]
                    }
                ):
                    if item[0]:
                        new_ds["linkedAlerts"].append(
                            {
                                "id": item[0],
                                "attributes": {
                                    "prsStore": item[2]["prsStore"][0]
                                }
                            }
                        )

            res["data"].append(new_ds)

        return res

    async def _get_routing_key_for_datastorage(self, ds_id: str) -> str:
        """Метод возвращает routing_key для определённого хранилища данных.

        Args:
            ds_id (str): id хранилища данных.

        Returns:
            str: _description_
        """
        item = await anext(self._hierarchy.search({
            "id": [ds_id],
            "attributes": ["prsJsonConfigString"]
        }))

        return json.loads(item[2]["prsJsonConfigString"][0])["routing_key"]

    async def _unlink_tag(self, tag_id: str) -> None:
        """Метод отвязки тега от хранилища.
        Ищем, к какому хранилищу привязан тег и посылаем этому хранилищу
        сообщение об отвязке, после удаляем ссылку на тег.

        Args:
            tag_id (str): id отвязываемого тега
        """
        item = await anext(self._hierarchy.search({
            "base": self._config.hierarchy["node_id"],
            "scope": hierarchy.CN_SCOPE_SUBTREE,
            "filter": f"&(cn={tag_id})(objectClass=prsDatastorageTagData)",
            "attributes": ["cn"]
        }))
        if not item[0]:
            self._logger.info(
                f"Тег {tag_id} не привязан ни к одному хранилищу."
            )
            return

        datastorage_id = await self._hierarchy.get_node_id(
            dn2str(str2dn(item[1])[2:])
        )

        routing_key = self._config["publish"]["main"]["routing_key"][0]

        await self._post_message(mes={"action": "unlinkTag", "id": [tag_id]},
            routing_key=routing_key)

        await self._hierarchy.delete(item[0])

        self._logger.info(
            f"Послано сообщение об отвязке тега {tag_id} "
            f"от хранилища {datastorage_id}"
        )

    async def _unlink_alert(self, alert_id: str) -> None:
        """Метод отвязки тревоги от хранилища.
        Ищем, к какому хранилищу привязана тревога и посылаем этому хранилищу
        сообщение об отвязке, после удаляем ссылку на тревогу.

        Args:
            alert_id (str): id отвязываемой тревоги
        """
        item = await anext(self._hierarchy.search({
            "base": self._config.hierarchy["node_id"],
            "scope": hierarchy.CN_SCOPE_SUBTREE,
            "filter": f"&(cn={alert_id})(objectClass=prsDatastorageAlertData)",
            "attributes": ["cn"]
        }))
        if not item[0]:
            self._logger.info(
                f"Тег {alert_id} не привязан ни к одному хранилищу."
            )
            return

        datastorage_id = await self._hierarchy.get_node_id(
            dn2str(str2dn(item[1])[2:])
        )

        routing_key = self._config["publish"]["main"]["routing_key"][0]

        await self._post_message(mes={"action": "unlinkTag", "id": [alert_id]},
            routing_key=routing_key)

        await self._hierarchy.delete(item[0])

        self._logger.info(
            f"Послано сообщение об отвязке тревоги {alert_id} "
            f"от хранилища {datastorage_id}"
        )

    async def _get_default_datastorage_id(self) -> str:
        item = await anext(
            self._hierarchy.search({
                "base": self._config.hierarchy["node_id"],
                "filter": {
                    "objectClass": ["prsDataStorage"],
                    "prsDefault": ["TRUE"]
                },
                "scope": hierarchy.CN_SCOPE_ONELEVEL
            })
        )
        return item[0]

    async def _link_tag(self, payload: dict) -> None:
        """Метод привязки тега к хранилищу.

        Логика работы метода: предполагаем, что тег может быть привязан только
        к одному хранилищу (может, есть смысл в привязке тега сразу к
        нескольким хранилищам, чтобы данные писались одновременно в разные
        хранилища; только тут возникает вопрос: при чтении данных, из
        какого хранилища эти данные брать).

        Если тег уже привязан к какому-либо хранилищу (ищем ссылку на этот тег
        в иерархии ``cn=dataStorages,cn=prs``), то сначала отвязываем тег от
        предыдущего хранилища, затем привязываем к новому.

        Args:
            payload (dict): {
                "id": "tag_id",
                "dataStorage_id": "ds_id",
                "attributes": {
                    "prsStore":
                }
            }
        """
        # если не передан datastorage_id, привязываем тег к хранилищу
        # по умолчанию
        if not payload.get("dataStorage_id"):
            datastorage_id = await self._get_default_datastorage_id()
            if not datastorage_id:
                self._logger.info(
                    f"Невозможно привязать тег: "
                    f"нет хранилища данных по умолчанию."
                )
                return
            payload["dataStorage_id"] = datastorage_id

        await self._unlink_tag(payload["id"])

        # res = {
        #   "prsStore": {...}
        # }
        # сообщение о привязке тега посылается с routing_key = <id хранилища>
        res = await self._post_message(
            mes={"action": "dataStorages.linkTag", "data": payload},
            reply=True,
            routing_key=payload["dataStorage_id"])

        prs_store = res.get("prsStore")
        tags_node_id = await self._hierarchy.get_node_id(
            f"cn=tags,cn=system,{self._hierarchy.get_node_dn(datastorage_id)}"
        )
        new_node_id = await self._hierarchy.add(
            base=tags_node_id,
            attribute_values={
                "objectCalss": ["prsDatastorageTagData"],
                "cn": payload["id"],
                "prsStore": prs_store
            }
        )
        await self._hierarchy.add_alias(
            parent_id=new_node_id,
            aliased_object_id=payload["id"],
            alias_name=payload["id"]
        )

        self._logger.info(
            f"Тег {payload['id']} привязан к хранилищу {datastorage_id}"
        )

    async def _link_alert(self, payload: dict) -> None:
        """Метод привязки тревоги к хранилищу.

        Логика работы метода: предполагаем, что тревога может быть привязана
        только
        к одному хранилищу (может, есть смысл в привязке тревог сразу к
        нескольким хранилищам, чтобы данные писались одновременно в разные
        хранилища; только тут возникает вопрос: при чтении данных, из
        какого хранилища эти данные брать).

        Если тревога уже привязана к какому-либо хранилищу (ищем ссылку на
        эту тревогу
        в иерархии ``cn=dataStorages,cn=prs``), то сначала отвязываем тревогу
        от предыдущего хранилища, затем привязываем к новому.

        Args:
            payload (dict): {
                "id": "alert_id",
                "attributes": {
                    "prsStore":
                }
            }
        """
        # если не передан datastorage_id, привязываем тег к хранилищу
        # по умолчанию
        if not datastorage_id:
            datastorage_id = await self._get_default_datastorage_id()
            if not datastorage_id:
                self._logger.info(
                    f"Невозможно привязать тревогу: "
                    f"нет хранилища данных по умолчанию."
                )
                return

        await self._unlink_alert(payload["id"])

        routing_key = self._config["publish"]["main"]["routing_key"][0]

        # res = {
        #   "prsStore": {...}
        # }
        res = await self._post_message(
            mes={"action": "linkAlert", "data": payload},
            reply=self._amqp_callback_queue.name,
            routing_key=routing_key)

        prs_store = res.get("prsStore")
        alerts_node_id = await self._hierarchy.get_node_id(
            f"cn=alerts,cn=system,{self._hierarchy.get_node_dn(datastorage_id)}"
        )
        new_node_id = await self._hierarchy.add(
            base=alerts_node_id,
            attribute_values={
                "objectCalss": ["prsDatastorageAlertData"],
                "cn": payload["id"],
                "prsStore": prs_store
            }
        )
        await self._hierarchy.add_alias(
            parent_id=new_node_id,
            aliased_object_id=payload["id"],
            alias_name=payload["id"]
        )

        self._logger.info(
            f"Тревога {payload['id']} привязана к хранилищу {datastorage_id}"
        )

    async def _further_create(self, mes: dict, new_id: str) -> None:
        sys_id = await anext(self._hierarchy.search({
            "base": new_id,
            "scope": hierarchy.CN_SCOPE_ONELEVEL,
            "filter": {
                "cn": ["system"]
            }
        }))

        sys_id = sys_id[0]

        await self._hierarchy.add(sys_id, {"cn": "tags"})
        await self._hierarchy.add(sys_id, {"cn": "alerts"})

        for item in mes["data"]["linkTags"]:
            copy_item = copy.deepcopy(item)
            copy_item["dataStorage_id"] = new_id
            await self._link_tag(copy_item)
        for item in mes["data"]["linkAlerts"]:
            copy_item = copy.deepcopy(item)
            copy_item["dataStorage_id"] = new_id
            await self._link_alert(copy_item)

settings = DataStoragesModelCRUDSettings()

app = DataStoragesModelCRUD(settings=settings, title="DataStoragesModelCRUD")
