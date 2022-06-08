import os

from minio import Minio

from config_common import on_before_startup, cache_prefix

from youwol_cdn_backend import Configuration, Constants

from youwol_utils import DocDbClient, AuthClient, CacheClient
from youwol_utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol_utils.context import DeployedContextReporter
from youwol_utils.http_clients.cdn_backend import LIBRARIES_TABLE
from youwol_utils.middlewares import Middleware
from youwol_utils.servers.fast_api import FastApiMiddleware, AppConfiguration, ServerOptions


async def get_configuration():

    required_env_vars = ["AUTH_HOST", "AUTH_CLIENT_ID", "AUTH_CLIENT_SECRET", "AUTH_CLIENT_SCOPE"]

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

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
    openid_host = os.getenv("AUTH_HOST")
    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = CacheClient(host="redis-master.infra.svc.cluster.local", prefix=cache_prefix)

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
                Middleware, {
                    "auth_client": auth_client,
                    "cache_client": cache_client,
                    # healthz need to not be protected as it is used for liveness prob
                    "unprotected_paths": lambda url: url.path.split("/")[-1] == "healthz"
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
