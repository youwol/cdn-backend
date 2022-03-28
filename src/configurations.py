import os
import sys
from dataclasses import dataclass
from typing import Union, Any, Coroutine, Dict

from youwol_cdn_backend import Constants
from youwol_utils import (
    find_platform_path, get_headers_auth_admin_from_env,
    get_headers_auth_admin_from_secrets_file, log_info,
)
from youwol_utils.clients.docdb.docdb import DocDbClient as DocDb
from youwol_utils.clients.docdb.local_docdb import LocalDocDbClient as LocalDocDb
from youwol_utils.clients.storage.local_storage import LocalStorageClient as LocalStorage
from youwol_utils.clients.storage.storage import StorageClient as Storage
from youwol_utils.context import ContextLogger, DeployedContextLogger
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.utils_paths import get_databases_path


@dataclass(frozen=True)
class Configuration:

    root_path: str
    http_port: int
    base_path: str
    storage: Union[Storage, LocalStorage, None]
    doc_db: Union[DocDb, LocalDocDb, None]
    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]

    replication_factor: int = 2
    ctx_logger: ContextLogger = DeployedContextLogger()


async def get_tricot_config() -> Configuration:
    required_env_vars = ["AUTH_HOST", "AUTH_CLIENT_ID", "AUTH_CLIENT_SECRET", "AUTH_CLIENT_SCOPE"]
    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")
    openid_host = os.getenv("AUTH_HOST")

    log_info("Use tricot configuration", openid_host=openid_host)

    storage = Storage(url_base="http://storage/api",
                      bucket_name=Constants.namespace
                      )

    doc_db = DocDb(url_base="http://docdb/api",
                   keyspace_name=Constants.namespace,
                   table_body=LIBRARIES_TABLE,
                   replication_factor=Configuration.replication_factor
                   )

    return Configuration(
        root_path='/api/cdn-backend',
        http_port=8080,
        base_path="",
        storage=storage,
        doc_db=doc_db,
        admin_headers=get_headers_auth_admin_from_env()
    )


async def get_remote_clients_config(url_cluster) -> Configuration:
    openid_host = "gc.auth.youwol.com"
    storage = Storage(url_base=f"https://{url_cluster}/api/storage",
                      bucket_name=Constants.namespace
                      )
    doc_db = DocDb(url_base=f"https://{url_cluster}/api/docdb",
                   keyspace_name=Constants.namespace,
                   table_body=LIBRARIES_TABLE,
                   replication_factor=Configuration.replication_factor
                   )

    return Configuration(
        root_path='/api/cdn-backend',
        http_port=2066,
        base_path="",
        storage=storage,
        doc_db=doc_db,
        admin_headers=get_headers_auth_admin_from_secrets_file(
            file_path=find_platform_path() / "secrets" / "tricot.json",
            url_cluster=url_cluster,
            openid_host=openid_host)
    )


async def get_remote_clients_gc_config() -> Configuration:
    return await get_remote_clients_config("gc.platform.youwol.com")


async def get_full_local_config() -> Configuration:

    database_path = await get_databases_path(sys.argv[2])

    storage = LocalStorage(root_path=database_path / 'storage',
                           bucket_name=Constants.namespace)

    doc_db = LocalDocDb(root_path=database_path / 'docdb',
                        keyspace_name=Constants.namespace,
                        table_body=LIBRARIES_TABLE)

    return Configuration(
        root_path='',
        http_port=2066,
        base_path="",
        storage=storage,
        doc_db=doc_db,
        admin_headers=None
    )


configurations = {
    'tricot': get_tricot_config,
    'remote-clients': get_remote_clients_gc_config,
    'full-local': get_full_local_config,
}

current_configuration = None


async def get_configuration():
    global current_configuration
    if current_configuration:
        return current_configuration

    current_configuration = await configurations[sys.argv[1]]()
    return current_configuration
