import requests
import logging
from urllib.parse import urljoin
# TODO: stop being coward and replace it with TRUE AIOHTTP REQUESTS

logger = logging.getLogger(__name__)


class KongApi(object):
    def __init__(self, kong_url):
        self.kong_url = kong_url
        self.session = requests.Session()

    def list_apis(self):
        r = self.session.get(urljoin(self.kong_url, "apis/"))

        # TODO: proper exceptions
        assert r.status_code in [200], r.status_code

        return r.json()

    def delete_apis(self):
        for endpoint in self.list_apis()["data"]:
            logging.debug(endpoint["id"])
            self.delete_api(endpoint["id"])

    def delete_api(self, api_id):
        r = self.session.delete(
            urljoin(self.kong_url, "apis/{}".format(api_id)))
        assert r.status_code in [204], r.status_code

    def add_api(self, request_path, upstream_url):
        r = self.session.post(
            urljoin(self.kong_url, "apis/"),
            data={
                "request_path": request_path,
                "strip_request_path": True,
                "preserve_host": False,
                "upstream_url": upstream_url
            }
        )
        assert r.status_code in [201], r.status_code
