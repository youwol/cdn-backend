import sys
from pathlib import Path

import aiohttp
from minio import Minio

from config_common import get_py_youwol_env, on_before_startup
from youwol_cdn_backend import Constants, Configuration
from youwol_utils import LocalDocDbClient
from youwol_utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol_utils.context import ConsoleContextReporter
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.servers.fast_api import AppConfiguration, ServerOptions


async def get_configuration():
    env = await get_py_youwol_env()
    databases_path = Path(env['pathsBook']['databases'])

    async def _on_before_startup():
        await on_before_startup(service_config)

    minio = Minio(
        endpoint="127.0.0.1:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )
    # make sure 'cdn' bucket exist
    buckets = minio.list_buckets()
    if not next((b.name == Constants.namespace for b in buckets), None):
        minio.make_bucket(bucket_name=Constants.namespace)

    py_youwol_port = sys.argv[2]
    async with aiohttp.ClientSession() as session:
        async with await session.get(url=f"http://localhost:{py_youwol_port}/admin/custom-commands/use-minio") as resp:
            if resp.status != 200:
                raise RuntimeError("Can not call 'use-minio' of py-youwol configuration")

    service_config = Configuration(
        file_system=MinioFileSystem(
            bucket_name=Constants.namespace,
            client=minio,
            root_path='youwol-users'
        ),
        doc_db=LocalDocDbClient(
            root_path=databases_path / 'docdb',
            keyspace_name=Constants.namespace,
            table_body=LIBRARIES_TABLE
        )
    )
    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['cdn-backend'],
        base_path="",
        middlewares=[],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
