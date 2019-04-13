import os

from twisted.web.resource import Resource

from settings import BASE_DIR


class PacResource(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader('Content-Type', 'text/plain;charset=UTF-8')
        with open(os.path.join(BASE_DIR, 'proxy.pac.js'), 'rb') as fp:
            return fp.read()
