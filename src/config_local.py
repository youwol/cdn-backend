from pathlib import Path
from config_common import get_py_youwol_env, on_before_startup
from youwol_cdn_backend import Constants, Configuration
from youwol_utils import LocalDocDbClient, LocalFileSystem
from youwol_utils.context import ConsoleContextReporter
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from youwol_utils.servers.fast_api import FastApiMiddleware, AppConfiguration, ServerOptions


async def get_configuration():
    env = await get_py_youwol_env()
    databases_path = Path(env['pathsBook']['databases'])

    file_system = LocalFileSystem(
        root_path=databases_path / 'storage' / Constants.namespace / 'youwol-users'
    )

    doc_db = LocalDocDbClient(
        root_path=databases_path / 'docdb',
        keyspace_name=Constants.namespace,
        table_body=LIBRARIES_TABLE
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        file_system=file_system,
        doc_db=doc_db
    )
    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['cdn-backend'],
        base_path="",
        middlewares=[FastApiMiddleware(AuthLocalMiddleware, {})],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
