import json
import ldap

from src.common.hierarchy import Hierarchy

class Cache(Hierarchy):

    def __init__(self, url: str, pool_size: int = 10):
        super().__init__(url, pool_size)
        self._cache_node_dn = None

    def connect(self) -> None:
        super().connect()

        with self._cm.connection() as conn:
            res = conn.search_s(base=self._base, scope=Hierarchy.CN_SCOPE_ONELEVEL,
                filterstr=f"(cn=_cache)",attrlist=['cn'])
            if not res:
                self.add(attribute_values={"cn": "_cache"})

        self._cache_node_dn = f"cn=_cache,{self._base}"

        return True

    async def get_key(self, key: str, json_loads: bool = False) -> str | dict | None:

        try:
            with self._cm.connection() as conn:
                base_node = f"cn={key},{self._cache_node_dn}"
                res = conn.search_s(base=base_node, scope=Hierarchy.CN_SCOPE_BASE,
                    attrlist=["prsJsonConfigString"])
            result = res[0][1]["prsJsonConfigString"][0].decode()
        except:
            return None

        if json_loads:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return None
        else:
            return result

    async def set_key(self, key: str, value: str | dict) -> None:
        new_value = (value, json.dumps(value, ensure_ascii=False))[isinstance(value, dict)]
        modlist = {
            "prsJsonConfigString": [new_value.encode('utf-8')]
        }
        modlist = ldap.modlist.addModlist(modlist)

        dn = f"cn={key},{self._cache_node_dn}"

        with self._cm.connection() as conn:
            try:
                conn.add_s(dn, modlist)
            except ldap.ALREADY_EXISTS:
                conn.modify_s(dn, modlist)

        return None
