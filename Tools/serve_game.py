"""Serve the published shared-C# browser build locally. No pip packages needed."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GameHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.wasm': 'application/wasm', '.json': 'application/json'}

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--directory', type=Path, default=ROOT / 'Web/publish/wwwroot')
    args = parser.parse_args()
    if not (args.directory / 'index.html').exists():
        raise SystemExit(f'Published game not found in {args.directory}. Run dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish first.')
    handler = functools.partial(GameHandler, directory=str(args.directory))
    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        print(f'Play at http://localhost:{args.port} — Ctrl+C stops the server.', flush=True)
        server.serve_forever()
