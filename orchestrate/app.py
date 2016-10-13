from aiohttp import web, ClientSession
import logging
from .configs.server_config import ServerConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def info(request):
    logger.debug(request.app["config"].ms_configs)
    return web.Response(body=b'Hello, world!', content_type='text/plain')


def configure_app(config_file="test_config.yaml"):
    app = web.Application()
    app.router.add_route("GET", "/info", info)

    app["config"] = ServerConfig(config_file)

    return app

if __name__ == '__main__':
    app = configure_app()
    web.run_app(app)
