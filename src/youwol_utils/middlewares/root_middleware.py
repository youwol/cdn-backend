from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from youwol_utils import YouwolHeaders
from youwol_utils.context import ContextFactory, Context, ContextLogger, Label
from youwol_utils.request_info_factory import request_info


class RootMiddleware(BaseHTTPMiddleware):
    ctx_logger: ContextLogger

    black_list = [
        "authorization"
    ]

    def __init__(
            self,
            app: ASGIApp,
            ctx_logger: ContextLogger,
            dispatch: DispatchFunction = None,
            **_
    ) -> None:
        super().__init__(app, dispatch)
        self.ctx_logger = ctx_logger

    def get_context(self, request: Request):
        root_id = YouwolHeaders.get_correlation_id(request)
        with_data = ContextFactory.with_static_data or {}
        return Context(request=request,
                       loggers=[self.ctx_logger],
                       parent_uid=root_id,
                       uid=root_id if root_id else 'root',
                       with_data=with_data)

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        context = self.get_context(request=request)
        info = request_info(request)

        async with context.start(
                action=info.message,
                with_attributes=info.attributes,
                with_labels=[Label.API_GATEWAY, *info.labels]
        ) as ctx:  # type: Context
            await ctx.info(
                text='incoming request',
                data={
                    'url': request.url.path,
                    'method': request.method,
                    'headers': {k: v if k.lower() not in self.black_list else "**black-listed**"
                                for k, v in request.headers.items()
                                }
                })
            response = await call_next(request)
            await ctx.info(f"Status code {response.status_code}")
            if response.status_code != 200:
                await ctx.failed(f"Request resolved to error {response.status_code}")

            return response
