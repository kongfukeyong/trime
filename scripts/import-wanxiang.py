#!/usr/bin/env python3
"""Import pinned offline resources. Development only; never shipped as runtime code.

Usage: python scripts/import-wanxiang.py [--source-dir PATH] [--allow-missing-model]
The default is strict: all archive/model/OpenCC hashes must match the lock file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

REPO = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=REPO.parent / 'work/wanxiang-source')
    parser.add_argument('--allow-missing-model', action='store_true', help='Stage the base only; NOT a release-ready resource set')
    args = parser.parse_args()
    lock = json.loads((REPO / 'docs/wanxiang-resources.lock.json').read_text(encoding='utf-8'))
    missing_model = False
    for entry in lock['downloads']:
        path = args.source_dir / entry['file']
        valid = path.is_file() and path.stat().st_size == entry['bytes'] and sha256(path) == entry['sha256']
        if not valid:
            if entry['role'] == 'model' and args.allow_missing_model:
                missing_model = True
                continue
            raise SystemExit(f'Missing/corrupt source: {path}; obtain the exact URL/hash in the lock file')

    dest = REPO / 'app/src/main/assets/rime'
    dest.mkdir(parents=True, exist_ok=True)
    owned = set()

    def put(name, data):
        output = dest / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        owned.add(name)

    with zipfile.ZipFile(args.source_dir / lock['downloads'][0]['file']) as archive:
        for item in archive.infolist():
            name = item.filename
            if item.is_dir() or '..' in Path(name).parts or name.startswith('/'):
                continue
            included = name.startswith(('dicts/', 'lua/', 'opencc/')) or name in {
                'default.yaml', 'custom_phrase.txt', 'version.txt',
                'wanxiang.schema.yaml', 'wanxiang.dict.yaml', 'wanxiang_algebra.yaml',
                'wanxiang_symbols.yaml', 'wanxiang_charset.schema.yaml', 'wanxiang_charset.dict.yaml',
                'wanxiang_mixedcode.schema.yaml', 'wanxiang_mixedcode.dict.yaml',
                'wanxiang_reverse.schema.yaml', 'wanxiang_reverse.dict.yaml',
            }
            if included:
                put(name, archive.read(item))
    # Package text OpenCC dictionaries: same OpenCC revision pinned by Trime.
    for entry in lock['downloads']:
        if entry['role'] == 'opencc-config':
            def text_dicts(value):
                if isinstance(value, dict):
                    return {key: ('text' if key == 'type' and val == 'ocd2' else
                                  val.removesuffix('.ocd2') + '.txt' if key == 'file' and isinstance(val, str) and val.endswith('.ocd2') else
                                  text_dicts(val)) for key, val in value.items()}
                if isinstance(value, list):
                    return [text_dicts(v) for v in value]
                return value
            config = json.loads((args.source_dir / entry['file']).read_text(encoding='utf-8'))
            put('opencc/' + Path(entry['file']).name, (json.dumps(text_dicts(config), ensure_ascii=False, indent=2) + '\n').encode())
        elif entry['role'] == 'opencc-dictionary':
            put('opencc/' + Path(entry['file']).name, (args.source_dir / entry['file']).read_bytes())
        elif entry['role'] == 'license':
            put('licenses/' + Path(entry['file']).name, (args.source_dir / entry['file']).read_bytes())
    put('default.custom.yaml', b'# Offline Wanxiang MVP; copied before DataManager creates its fallback.\npatch:\n  schema_list:\n    - schema: wanxiang\n  menu/page_size: 6\n')
    model = next(e for e in lock['downloads'] if e['role'] == 'model')
    if not missing_model:
        shutil.copyfile(args.source_dir / model['file'], dest / model['file'])
        owned.add(model['file'])
    put('licenses/WANXIANG-NOTICE.txt', (
        'Wanxiang Pinyin v13.1.0 by amzxyz and contributors; CC-BY-4.0.\n'
        'https://github.com/amzxyz/rime-wanxiang/tree/ced3589c2b6222e46001d32430aa297477770184\n'
        'Wanxiang LTS Simplified Chinese language model by amzxyz; CC-BY-4.0.\n'
        'https://github.com/amzxyz/RIME-LMDG/releases/tag/LTS\n'
        'Model asset ID 636982290; SHA256 20aca767f06ab2abdccce5ea9c45af5364114a37e25bb7c6de40e4f328be029e\n'
        'OpenCC by BYVoid and contributors; Apache-2.0, revision 907bfcbbd3aae86ff04bc8eaca67c8af03108ddf.\n'
        'https://github.com/BYVoid/OpenCC/tree/907bfcbbd3aae86ff04bc8eaca67c8af03108ddf\n'
        'Integration changes: select the base full-pinyin resources; add default.custom.yaml;\n'
        'supply text-format OpenCC configs/dictionaries. Original dictionaries, Lua, and gram are unchanged.\n'
        'See bundled licenses and docs/wanxiang-mvp.md for provenance and limitations.\n'
    ).encode())
    manifest = {
        'model_complete': not missing_model,
        'files': [{'path': n, 'bytes': (dest / n).stat().st_size, 'sha256': sha256(dest / n)} for n in sorted(owned)],
    }
    (REPO / 'docs/wanxiang-assets.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported {len(owned)} files, {sum(f["bytes"] for f in manifest["files"]):,} bytes; model_complete={not missing_model}')
    if missing_model:
        print('BASE STAGING ONLY. Rerun without --allow-missing-model before packaging.')


if __name__ == '__main__':
    main()
