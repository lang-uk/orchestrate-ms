import os.path
import asyncio
import logging
import aiohttp
import aiohttp_jinja2
from collections import defaultdict
from copy import deepcopy
from slugify import slugify
from urllib.parse import urljoin

import jsonschema.exceptions
from .swagger_config import SwaggerConfig
from .tools import deserialize_me, validate_me
from .exc import ConfigReaderException
from .output_schema import GLOBAL_SWAGGER_INFO
logger = logging.getLogger(__name__)


class ServerConfig(object):
    def __init__(self, config_file):
        # Read and deserialize config
        try:
            with open(config_file, "r") as fp:
                self.config = deserialize_me(fp.read())
        except ValueError:
            raise ConfigReaderException("Cannot deserialize config")
        except OSError:
            raise ConfigReaderException("Cannot read config")

        # Validate it against schema
        config_validator_file = os.path.join(
            os.path.dirname(__file__), "schemas/validate_server_config.json")

        try:
            validate_me(self.config, config_validator_file)
        except jsonschema.exceptions.ValidationError:
            raise ConfigReaderException("Cannot validate config")

        self.ms_configs = []
        loop = asyncio.get_event_loop()
        with aiohttp.ClientSession(loop=loop) as session:
            self.ms_configs = [
                SwaggerConfig(config_url, session)
                for config_url in self.config["microservices"]]

            tasks = [asyncio.ensure_future(ms_config.load(
                     self.config.get("skip_swagger_validation", False)))
                     for ms_config in self.ms_configs]

            loop.run_until_complete(asyncio.gather(*tasks))

        logger.debug("Succesfully loaded {} swagger configs out of {}".format(
            len(tuple(self.good_configs())),
            len(self.ms_configs)
        ))

    def good_configs(self):
        for config in self.ms_configs:
            if config.is_ok and config.loaded:
                yield config

    def generate_global_config(self, request):
        # Bloody aiohttp_jinja2, why do you need request at all?
        global_config = deepcopy(GLOBAL_SWAGGER_INFO)

        global_config["info"]["description"] = aiohttp_jinja2.render_string(
            "description.jinja2", request, {
                "configs": self.good_configs()
            })

        paths = defaultdict(lambda: defaultdict(dict))
        definitions = {}

        for config in self.good_configs():
            url = config.base_url

            # TODO: PREFIX!!!
            definitions.update(config.swagger_config.get("definitions", {}))

            for path, path_config in config.swagger_config.get("paths", {}).items():
                for method, method_config in path_config.items():
                    if ("x-taskClass" not in method_config or
                            "x-taskAlgo" not in method_config):
                        logger.warning(
                            "Method {} of endpoint {} of microservice {} doesn't have x-Tags, skipping it".format(
                                method, path, url
                            )
                        )
                        continue

                    task_class = method_config["x-taskClass"]
                    task_algo = method_config["x-taskAlgo"]
                    # TODO: unique instead of default?
                    task_model = method_config.get("x-taskModel", "default")
                    new_url = "/{}/{}/{}".format(
                        slugify(task_class),
                        slugify(task_algo),
                        slugify(task_model)
                    )

                    if new_url in paths and method in paths[new_url]:
                        logger.warning(
                            "Endpoint {} of microservice {} already exist, skipping it".format(
                                new_url, url
                            )
                        )
                        continue

                    paths[new_url][method] = method_config

        global_config["paths"] = paths
        global_config["definitions"] = definitions
        return global_config

    def generate_proxy_config(self):
        proxies = []
        paths = defaultdict(lambda: defaultdict(dict))

        for config in self.good_configs():
            url = config.base_url

            for path, path_config in config.swagger_config.get("paths", {}).items():
                for method, method_config in path_config.items():
                    if ("x-taskClass" not in method_config or
                            "x-taskAlgo" not in method_config):
                        logger.warning(
                            "Method {} of endpoint {} of microservice {} doesn't have x-Tags, skipping it".format(
                                method, path, url
                            )
                        )
                        continue

                    task_class = method_config["x-taskClass"]
                    task_algo = method_config["x-taskAlgo"]
                    # TODO: unique instead of default?
                    # How to syncronize with them with generate_global_config then?
                    task_model = method_config.get("x-taskModel", "default")
                    new_url = "/{}/{}/{}".format(
                        slugify(task_class),
                        slugify(task_algo),
                        slugify(task_model)
                    )

                    if new_url in paths and method in paths[new_url]:
                        continue

                    # TODO: That shit screams: refactor me!
                    # We need an iterator which then can be used by both methods
                    # generate_global_config and generate_proxy_config
                    paths[new_url][method] = method_config
                    proxies.append({
                        "method": method,
                        "new_url": new_url,
                        # TODO: check how it should work
                        "old_url": urljoin(url, path.lstrip("/"))
                    })

        return proxies
