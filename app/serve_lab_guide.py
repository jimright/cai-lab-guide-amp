"""Serve the built lab guide as a static site.

Adapted from ref/serve_lab_guide.py: same CDSW_APP_PORT / 127.0.0.1 pattern,
but LAB_GUIDE_DIR now defaults to the fixed build output path written by
cml/build_lab_guide.py. Every request checks the directory fresh (not just
at startup), so once the build job succeeds -- whether at import time or
hours later after a manual upload -- this already-running app starts
serving real content immediately, with no restart.
"""
import http.server
import os
import pathlib
import socketserver

PORT = int(os.environ.get("CDSW_APP_PORT", "8080"))
DIRECTORY = os.environ.get("LAB_GUIDE_DIR", "/home/cdsw/lab_guide_site")

NOT_BUILT_YET_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Lab Guide - Not Built Yet</title></head>
<body style="font-family: sans-serif; max-width: 40em; margin: 4em auto;">
  <h1>Guide not built yet</h1>
  <p>Run the <strong>Build lab guide site</strong> job, then refresh this
     page.</p>
</body>
</html>
"""


def _site_is_built() -> bool:
    """True iff DIRECTORY exists, is a directory, and has at least one entry."""
    directory = pathlib.Path(DIRECTORY)
    if not directory.is_dir():
        return False
    return any(directory.iterdir())


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if not _site_is_built():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(NOT_BUILT_YET_HTML)))
            self.end_headers()
            self.wfile.write(NOT_BUILT_YET_HTML)
            return
        super().do_GET()


print(f"Serving pre-built site from '{DIRECTORY}' on port {PORT}...")

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()
