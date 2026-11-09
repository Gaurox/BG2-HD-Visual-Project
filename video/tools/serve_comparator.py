"""Aperçu local avec HTTP Range pour la navigation dans les vidéos."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        self.byte_count = None
        value = self.headers.get('Range')
        path = Path(self.translate_path(self.path))
        if not value or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
        if not match or not any(match.groups()):
            self.send_error(416)
            return None
        a, b = match.groups()
        start = int(a) if a else max(0, size-int(b))
        end = min(int(b), size-1) if a and b else size-1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        stream = path.open('rb')
        stream.seek(start)
        self.byte_count = end-start+1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Length', str(self.byte_count))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        return stream

    def copyfile(self, source, outputfile):
        if self.byte_count is None:
            return super().copyfile(source, outputfile)
        left = self.byte_count
        while left:
            chunk = source.read(min(left, 1024*1024))
            if not chunk:
                break
            outputfile.write(chunk)
            left -= len(chunk)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 8768), partial(Handler, directory=str(root)))
    print('http://127.0.0.1:8768/tools/comparator.html', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
