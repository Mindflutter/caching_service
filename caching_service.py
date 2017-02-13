from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urlparse import urlparse, parse_qs, urljoin
from cachetools import TTLCache

import requests
import threading


SIDE_SERVICE_URL = "https://vast-eyrie-4711.herokuapp.com/"
CACHE_MAXSIZE = 10000
TTL = 24*60*60


class NoValue(Exception):
    pass


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


class SideServiceHandler(object):
    """ Handler to manage communications with the side service.
        Keeps a cache of results in the following format:
             {'<key>': {'value': '<hash>', 'queried': <True|False>}}
    """

    def __init__(self):
        self.url = SIDE_SERVICE_URL
        self.cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=TTL)

    def get_value_from_cache(self, key):
        """ Get key info from cache. If key is not available, launch a separate thread with request to side service """
        try:
            return self.cache[key]['value']
        except KeyError:
            self.get_from_url(key)
            raise NoValue

    @threaded
    def get_from_url(self, key):
        """ Query URL, return response status. Threaded method. """
        req_url = urljoin(self.url, "?key={0}".format(key))
        if key in self.cache and self.cache[key]['queried']:
            return
        else:
            self.cache[key] = {'queried': True}
            try:
                print "Querying side service, key", key
                response = requests.get(req_url)
                response.raise_for_status()
                value = response.json()['hash']
                print "Got value", value, "for key", key
                self.cache[key]['value'] = value
            except Exception, error:
                print error
            finally:
                self.cache[key]['queried'] = False


class UserRequestHandler(BaseHTTPRequestHandler):

    side_service_handler = SideServiceHandler()

    def do_GET(self):
        """ Method handling GET requests from users. """
        url_path = urlparse(self.path)
        if url_path.path != '/from_cache':
            print 'Unknown endpoint'
            self.send_response(404)
            return
        key = parse_qs(url_path.query)['key'][0]

        try:
            cached_value = self.side_service_handler.get_value_from_cache(key)
            self.send_success(cached_value)
        except NoValue:
            self.send_retry()

    def send_success(self, body):
        """ Successful outcome. Send response 200 and write result body. """
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def send_retry(self):
        """ No result value. Send response 304. """
        self.send_response(304)
        self.send_header('Retry-after', 10)
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """ HTTP server extension that handles requests in a separate thread. """

if __name__ == '__main__':
    server = ThreadedHTTPServer(('localhost', 8000), UserRequestHandler)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()
