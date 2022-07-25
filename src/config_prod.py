import os

from minio import Minio

from config_common import on_before_startup
from youwol_cdn_backend import Configuration, Constants
from youwol_utils import DocDbClient
from youwol_utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol_utils.clients.oidc.oidc_config import OidcInfos, PrivateClient
from youwol_utils.context import DeployedContextReporter
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.middlewares import AuthMiddleware
from youwol_utils.servers.fast_api import AppConfiguration, ServerOptions, FastApiMiddleware


async def get_configuration():
    required_env_vars = [
        "OPENID_BASE_URL",
        "OPENID_CLIENT_ID",
        "OPENID_CLIENT_SECRET",
        "MINIO_HOST_PORT",
        "MINIO_ACCESS_KEY",
        "MINIO_ACCESS_SECRET"
    ]

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    openid_infos = OidcInfos(
        base_uri=os.getenv("OPENID_BASE_URL"),
        client=PrivateClient(
            client_id=os.getenv("OPENID_CLIENT_ID"),
            client_secret=os.getenv("OPENID_CLIENT_SECRET")
        )
    )

    file_system = MinioFileSystem(
        bucket_name=Constants.namespace,
        # this root path is for backward compatibility
        root_path="youwol-users/",
        client=Minio(
            endpoint=os.getenv("MINIO_HOST_PORT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_ACCESS_SECRET"),
            secure=False
        )
    )
    doc_db = DocDbClient(
        url_base="http://docdb/api",
        keyspace_name=Constants.namespace,
        table_body=LIBRARIES_TABLE,
        replication_factor=2
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        file_system=file_system,
        doc_db=doc_db
    )

    server_options = ServerOptions(
        root_path='/api/cdn-backend',
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                AuthMiddleware, {
                    'openid_infos': openid_infos,
                    'predicate_public_path': lambda url:
                    url.path.endswith("/healthz")
                }
            )
        ],
        on_before_startup=_on_before_startup,
        ctx_logger=DeployedContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
