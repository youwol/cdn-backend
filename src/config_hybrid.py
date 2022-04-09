from config_common import get_py_youwol_env, on_before_startup, cache_prefix

from youwol_cdn_backend import Constants, Configuration
from youwol_utils import StorageClient, DocDbClient, AuthClient, LocalCacheClient
from youwol_utils.context import ConsoleContextLogger
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.middlewares import Middleware
from youwol_utils.servers.fast_api import FastApiMiddleware, AppConfiguration, ServerOptions


async def get_configuration():

    env = await get_py_youwol_env()
    openid_host = env['k8sInstance']['openIdConnect']['host']
    url_cluster = env['k8sInstance']['host']

    storage = StorageClient(url_base=f"https://{url_cluster}/api/storage",
                            bucket_name=Constants.namespace
                            )
    doc_db = DocDbClient(url_base=f"https://{url_cluster}/api/docdb",
                         keyspace_name=Constants.namespace,
                         table_body=LIBRARIES_TABLE,
                         replication_factor=2
                         )

    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = LocalCacheClient(prefix=cache_prefix)

    service_config = Configuration(
        storage=storage,
        doc_db=doc_db
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['cdn-backend'],
        base_path="",
        middlewares=[FastApiMiddleware(Middleware, {
            "auth_client": auth_client,
            "cache_client": cache_client
        })],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextLogger()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
