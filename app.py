import tornado.ioloop
import tornado.web

import sockjs.tornado

from Queue import Queue, Empty
import json

QUEUE = Queue()


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class GitlabWebhookHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        repo = data['repository']['name']
        push_user = data['user_name']
        commits = data['commits']
        message = json.dumps({'type': 'gitlab', 'repo': repo, 'push_user': push_user, 'commits': commits})
        QUEUE.put(message)
        self.write('ok')


class SocketConnection(sockjs.tornado.SockJSConnection):
    """Chat connection implementation"""
    # Class level variable
    participants = set()

    def on_open(self, info):
    # Add client to the clients list
        self.participants.add(self)
        self.timeout = tornado.ioloop.PeriodicCallback(self._hook, 500)
        self.timeout.start()

    def on_close(self):
        # Remove client from the clients list and broadcast leave message
        self.participants.remove(self)

    def _hook(self):
        try:
            while True:
                self.broadcast(self.participants, QUEUE.get(block=False))
        except Empty:
            pass


if __name__ == '__main__':
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    SocketRouter = sockjs.tornado.SockJSRouter(SocketConnection, '/socket')

    app = tornado.web.Application(
        [(r"/", IndexHandler), (r"/gitlab", GitlabWebhookHandler)] + SocketRouter.urls
    )

    app.listen(8080)

    tornado.ioloop.IOLoop.instance().start()