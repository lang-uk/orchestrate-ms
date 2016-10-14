import os.path
import logging
from aiodns.error import DNSError
import jsonschema.exceptions
from urllib.parse import urlparse, urlunparse
from .exc import IncompatibleSwaggerException
from .tools import deserialize_me, validate_me

logger = logging.getLogger(__name__)


class SwaggerConfig(object):
    def __init__(self, url, session):
        self.url = url
        self.session = session
        self.loaded = False
        self.is_ok = False
        self.validator_file = os.path.join(
            os.path.dirname(__file__), "schemas/validate_swagger.json")

    async def load(self, skip_validation=False):
        try:
            async with self.session.get(self.url) as resp:
                self.loaded = True

                if resp.status != 200:
                    logger.warning(
                        "Cannot load swagger file from {}, status {}".format(
                            self.url, resp.status))

                try:
                    obj = deserialize_me(await resp.text())
                except ValueError:
                    logger.warning(
                        "Cannot parse swagger file from {}".format(self.url))

                try:
                    validate_me(obj, self.validator_file)
                    self.is_ok = True
                    self.swagger_config = obj
                except jsonschema.exceptions.ValidationError:
                    logger.warning(
                        "Cannot validate swagger file from {}".format(self.url))

                    if skip_validation:
                        logger.warning(
                            "Adding swagger file from {} anyway".format(self.url))
                        self.is_ok = True
                        self.swagger_config = obj

        except (DNSError, ValueError) as e:
            logger.warning(
                "Cannot resolve url for swagger file from {}\n{}".format(
                    self.url, e))

    @property
    def base_url(self):
        assert self.loaded and self.is_ok

        res = urlparse(self.url)
        scheme = res.scheme

        if "schemes" in self.swagger_config:
            if ("http" not in self.swagger_config["schemes"] and
                    "https" not in self.swagger_config["schemes"]):
                raise IncompatibleSwaggerException(
                    "We are only supporting http and https at the moment")

            # We prefer https over http
            if "https" in self.swagger_config["schemes"]:
                scheme = "https"

        netloc = self.swagger_config.get("host", res.netloc)

        # TODO: check how that should work
        base_path = self.swagger_config.get("basePath", "/") + "/"
        logger.error(urlunparse([scheme, netloc, base_path, "", "", ""]))

        return urlunparse([scheme, netloc, base_path, "", "", ""])
