from aiohttp import web, ClientSession
import logging
import os.path
import jinja2
import aiohttp_jinja2
from urllib.parse import urljoin
from .kong_client import KongApi
from .models.server_config import ServerConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def info(request):
    urls = [config.base_url
            for config in request.app["config"].good_configs()]

    return web.json_response(
        {
            "urls": urls,
            "kong_urls": request.app["kong_client"].list_apis()
        }
    )


async def swagger(request):
    return web.json_response(
        request.app["config"].generate_global_config(request)
    )


def configure_app(config_file="test_config.yaml"):
    app = web.Application()
    app.router.add_route("GET", "/swagger.json", swagger)

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(
            os.path.join(
                os.path.dirname(__file__),
                "templates/"
            )
        )
    )

    config_obj = ServerConfig(config_file)
    app["config"] = config_obj

    kong_client = KongApi(config_obj.config["kong_api_url"])
    app["kong_client"] = kong_client

    logger.debug("Deleting all apis from kong")
    kong_client.delete_apis()
    logger.debug("Deleted all apis from kong")
    for proxy in config_obj.generate_proxy_config():
        # TODO: POST vs GET on the same request_path

        logger.debug("Adding proxy from {} to {}".format(
            proxy["new_url"], proxy["old_url"]
        ))

        kong_client.add_api(proxy["new_url"], proxy["old_url"])

    kong_client.add_api(
        "/swagger.json",
        urljoin(config_obj.config["base_url"], "swagger.json")
    )

    if config_obj.config.get("debug"):
        app.router.add_route("GET", "/info", info)

    logger.info(app["config"].generate_proxy_config())

    return app

if __name__ == '__main__':
    app = configure_app()
    web.run_app(app)
