import yaml
import json
import logging

logger = logging.getLogger(__name__)

class SwaggerConfig(object):
    def __init__(self, url, session):
        self.url = url
        self.session = session

    async def load(self):
        async with self.session.get(self.url) as resp:
            logger.debug(resp.status)
            logger.debug(len(await resp.text()))
