"""Verify local assets, or restore pinned npm browser assets with --restore."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

root = Path(__file__).resolve().parents[1] / 'projects/static/vendor'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--restore', action='store_true', help='Download the exact pinned archives and restore selected files.')
args = parser.parse_args()
for package in json.loads((root / 'manifest.json').read_text()):
    if args.restore:
        with urllib.request.urlopen(package['url'], timeout=60) as response:
            blob = response.read()
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(blob).digest()).decode()
        if integrity != package['integrity']:
            raise SystemExit(f"Integrity mismatch: {package['package']}")
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            for entry in package['files']:
                content = archive.extractfile(entry['source']).read()
                destination = root / entry['path']
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
    for entry in package['files']:
        if hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit(f"File mismatch: {entry['path']}")
    print(f"OK {package['package']} {package['version']}")
