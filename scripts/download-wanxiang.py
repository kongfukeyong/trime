#!/usr/bin/env python3
"""Development/CI only: fetch exactly the resources pinned in the lock file."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

REPO = Path(__file__).resolve().parents[1]


def valid(path, entry):
    if not path.is_file() or path.stat().st_size != entry['bytes']:
        return False
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    return digest == entry['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=REPO.parent / 'work/wanxiang-source')
    args = parser.parse_args()
    lock = json.loads((REPO / 'docs/wanxiang-resources.lock.json').read_text(encoding='utf-8'))
    for entry in lock['downloads']:
        output = args.source_dir / entry['file']
        if valid(output, entry):
            print(f'Cached and verified: {entry["file"]}', flush=True)
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        partial = output.with_name(output.name + '.partial')
        for attempt in range(3):
            try:
                request = urllib.request.Request(entry['url'], headers={'User-Agent': 'Trime-MVP-resource-build'})
                with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as target:
                    while chunk := response.read(1024 * 1024):
                        target.write(chunk)
                if not valid(partial, entry):
                    raise RuntimeError(f'Pinned checksum/size mismatch for {entry["file"]}; refusing an unpinned update')
                partial.replace(output)
                print(f'Downloaded and verified: {entry["file"]}', flush=True)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))


if __name__ == '__main__':
    main()
