from aiohttp import web, ClientSession
import logging
import os.path
import jinja2
import aiohttp_jinja2
from .models.server_config import ServerConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def info(request):
    urls = [config.base_url
            for config in request.app["config"].good_configs()]

    return web.json_response(
        urls
    )


async def swagger(request):
    return web.json_response(
        request.app["config"].generate_global_config(request)
    )


def configure_app(config_file="test_config.yaml"):
    app = web.Application()
    app.router.add_route("GET", "/info", info)
    app.router.add_route("GET", "/swagger", swagger)

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(
            os.path.join(
                os.path.dirname(__file__),
                "templates/"
            )
        )
    )

    app["config"] = ServerConfig(config_file)

    return app

if __name__ == '__main__':
    app = configure_app()
    web.run_app(app)
