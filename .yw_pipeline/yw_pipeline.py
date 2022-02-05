from youwol.environment.models import IPipelineFactory
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.pipelines.pipeline_fastapi_youwol_backend import pipeline, PipelineConfig
from youwol_utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, env: YouwolEnvironment, context: Context):
        async with context.start(
                action="Pipeline creation for cdn-backend",
                with_attributes={'project': 'cdn-backend'}
        ) as ctx:  # type: Context
            config = PipelineConfig(
                tags=["cdn-apps-server"],
                k8sInstance=env.k8sInstance,
                targetDockerRepo="gitlab-docker-repo"
            )
            await ctx.info(text='Pipeline config', data=config)
            result = pipeline(config, ctx)
            await ctx.info(text='Pipeline', data=result)
            return result
