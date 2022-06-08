from youwol_cdn_backend import get_router
from youwol_utils.servers.fast_api import serve, FastApiApp, FastApiRouter, AppConfiguration, \
    select_configuration_from_command_line


async def local() -> AppConfiguration:
    from config_local import get_configuration as config
    return await config()


async def local_minio() -> AppConfiguration:
    from config_local_minio import get_configuration as config
    return await config()


async def hybrid() -> AppConfiguration:
    from config_hybrid import get_configuration as config
    return await config()


async def prod() -> AppConfiguration:
    from config_prod import get_configuration as config
    return await config()


app_config = select_configuration_from_command_line(
    {
        "local": local,
        "hybrid": hybrid,
        "local-minio": local_minio,
        "prod": prod
    }
)

serve(
    FastApiApp(
        title="cdn-backend",
        description="Content delivery network service & dependencies resolution",
        server_options=app_config.server,
        root_router=FastApiRouter(
            router=get_router(app_config.service)
        )
    )
)
