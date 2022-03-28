import asyncio
from configurations import get_configuration, Configuration
from youwol_cdn_backend import init_resources, router, Dependencies
from youwol_utils.servers.fast_api import serve, FastApiApp, FastApiRouter


configuration: Configuration = asyncio.get_event_loop().run_until_complete(get_configuration())
asyncio.get_event_loop().run_until_complete(init_resources(configuration))

Dependencies.get_configuration = get_configuration

serve(
    FastApiApp(
        title="cdn-backend",
        description="CDN service of YouWol",
        root_path=configuration.root_path,
        base_path=configuration.base_path,
        root_router=FastApiRouter(
            router=router
        ),
        ctx_logger=configuration.ctx_logger,
        http_port=configuration.http_port
    )
)
