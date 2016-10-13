import os.path
import json
import asyncio
import aiohttp
from jsonschema import validate as schema_validate

from .swagger_config import SwaggerConfig
from .tools import deserialize_me
from .exc import ConfigReaderException


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
        config_validator = os.path.join(
            os.path.dirname(__file__), "schemas/validate_server_config.json")

        with open(config_validator, "r") as fp:
            if schema_validate(self.config, json.load(fp)) is not None:
                raise ConfigReaderException("Cannot validate config")

        self.ms_configs = []
        loop = asyncio.get_event_loop()
        with aiohttp.ClientSession(loop=loop) as session:
            self.ms_configs = [
                SwaggerConfig(config_url, session)
                for config_url in self.config["microservices"]]

            tasks = [asyncio.ensure_future(ms_config.load())
                     for ms_config in self.ms_configs]

            loop.run_until_complete(asyncio.gather(*tasks))
