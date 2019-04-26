import os

from twisted.web.resource import Resource

from config import ConfigManager
from settings import BASE_DIR

conf = ConfigManager().default


class PacResource(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader('Content-Type', 'text/plain;charset=UTF-8')
        with open(os.path.join(BASE_DIR, 'pac.txt'), 'rb') as fp:
            js = fp.read()
            pac_proxy = conf.get('local', 'pac_proxy').encode()
            js = js.replace(b"__PROXY__", pac_proxy)
            return js
