"""Read-only local preview server, restricted to this batch's review folder."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import os
from temporal import ROOT,BATCH,save


if __name__=='__main__':
    review=BATCH/'review'
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(review)))
    url=f'http://127.0.0.1:{server.server_port}/index.html'
    save(ROOT/'tmp/lot64-review-server.json',{'url':url,'root':str(review),'pid':os.getpid()})
    print(url,flush=True)
    server.serve_forever()
