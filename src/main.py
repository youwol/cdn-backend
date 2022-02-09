import asyncio
import itertools

import uvicorn
from fastapi import FastAPI, Depends
from starlette.requests import Request

from youwol_cdn.configurations import get_configuration, Configuration
from youwol_cdn.resources_initialization import init_resources
from youwol_cdn.root_paths import router as cdn_router
from youwol_utils import (YouWolException, log_info, youwol_exception_handler)
from youwol_utils.middlewares.root_middleware import RootMiddleware
from youwol_utils.utils_paths import matching_files, FileListing, files_check_sum

flatten = itertools.chain.from_iterable

configuration: Configuration = asyncio.get_event_loop().run_until_complete(get_configuration())
asyncio.get_event_loop().run_until_complete(init_resources(configuration))

app = FastAPI(
    title="cdn-backend",
    description="CDN service of YouWol",
    openapi_prefix=configuration.open_api_prefix)


@app.exception_handler(YouWolException)
async def exception_handler(request: Request, exc: YouWolException):
    return await youwol_exception_handler(request, exc)


app.add_middleware(RootMiddleware, ctx_logger=configuration.ctx_logger)

app.include_router(
    cdn_router,
    prefix=configuration.base_path,
    dependencies=[Depends(get_configuration)],
    tags=[]
)

files_src_check_sum = matching_files(
    folder="./",
    patterns=FileListing(
        include=['*'],
        # when deployed using dockerfile there is additional files in ./src: a couple of .* files and requirements.txt
        ignore=["requirements.txt", "tmp_zips", "youwol_cdn/initial_resources", ".*", "*.pyc"]
    )
)

log_info(f"./src check sum: {files_check_sum(files_src_check_sum)} ({len(files_src_check_sum)} files)")

if __name__ == "__main__":
    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=configuration.http_port)
