#!/usr/bin/env python3
"""Static, offline dependency/integrity audit. Requires development-only PyYAML."""
import hashlib
import json
from pathlib import Path
import re
import sys
import yaml

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'app/src/main/assets/rime'
errors = []
checks = 0


def need(relative, reason):
    global checks
    checks += 1
    if not (ROOT / relative).is_file():
        errors.append(f'{reason}: missing {relative}')


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


configs = {}
dict_entries = {}
for path in sorted(ROOT.rglob('*.yaml')):
    text = path.read_text(encoding='utf-8-sig')
    if path.name.endswith('.dict.yaml'):
        head, _, body = text.partition('\n...')
        data = yaml.safe_load(head)
        dict_entries[path.relative_to(ROOT).as_posix()] = sum(1 for line in body.splitlines() if '\t' in line and not line.startswith('#'))
    else:
        data = yaml.safe_load(text)
    configs[path.relative_to(ROOT).as_posix()] = data
    for key, value in walk(data):
        if key == 'dictionary' and isinstance(value, str) and value:
            need(value + '.dict.yaml', str(path.name))
        elif key == 'import_tables':
            for table in value:
                need(table + '.dict.yaml', str(path.name))
        elif key == 'dependencies':
            for schema in value:
                need(schema + '.schema.yaml', str(path.name))
        elif key == 'import_preset' and isinstance(value, str):
            need(value + '.yaml', str(path.name))
        elif key in ('__include', '__patch'):
            for ref in strings(value):
                if ':/' in ref:
                    name, node = ref.split(':/', 1)
                    if name:
                        need(name + '.yaml', str(path.name))
        elif key == 'opencc_config':
            need('opencc/' + value, str(path.name))
        elif key == 'language':
            need(value + '.gram', str(path.name))
    for module in re.findall(r'lua_(?:processor|translator|filter)@\*([\w/]+)', text):
        need('lua/' + module + '.lua', str(path.name))

# Check include/patch target keys, not just filenames (the '?' suffix means optional).
for name, data in configs.items():
    for key, value in walk(data):
        if key not in ('__include', '__patch'):
            continue
        for ref in strings(value):
            if ':/' not in ref or ref.endswith('?'):
                continue
            target, node = ref.split(':/', 1)
            current = configs.get(target + '.yaml') if target else data
            for component in node.split('/'):
                if not component:
                    continue
                if not isinstance(current, dict) or component not in current:
                    errors.append(f'{name}: unresolved config key {ref}')
                    break
                current = current[component]

for path in ROOT.glob('opencc/*.json'):
    for key, value in walk(json.loads(path.read_text(encoding='utf-8'))):
        if key == 'file':
            need('opencc/' + value, path.name)

for path in ROOT.rglob('*.lua'):
    text = path.read_text(encoding='utf-8-sig')
    for module in re.findall(r'\brequire\s*\(?\s*[\'"]([^\'"]+)[\'"]', text):
        need('lua/' + module.replace('.', '/') + '.lua', path.name)
    # Ignore comments and the optional built-in bit/bit32 pcall(require, ...) fallbacks.
    code = '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('--'))
    if re.search(r'\b(?:socket|http)\s*\.\s*(?:connect|request)|\bcurl\b|\bwget\b|io\.popen', code):
        errors.append(f'{path.name}: unexpected networking/process code; manual review required')

for name in ('custom_phrase.txt', 'dicts/chengyu.txt', 'lua/tips/tips_show.txt', 'version.txt'):
    need(name, 'Lua/table data')

model_path = ROOT / 'wanxiang-lts-zh-hans.gram'
if model_path.is_file():
    with model_path.open('rb') as model:
        expected_header = b'Rime::Grammar/1.0\x00'
        if model.read(len(expected_header)) != expected_header:
            errors.append('Model is not a Rime::Grammar/1.0 binary')

manifest = json.loads((REPO / 'docs/wanxiang-assets.manifest.json').read_text(encoding='utf-8'))
if not manifest['model_complete']:
    errors.append('Manifest marks the model incomplete')
for entry in manifest['files']:
    path = ROOT / entry['path']
    if not path.is_file():
        errors.append(f'Manifest missing file: {entry["path"]}')
        continue
    with path.open('rb') as file:
        actual = hashlib.file_digest(file, 'sha256').hexdigest()
    if path.stat().st_size != entry['bytes'] or actual != entry['sha256']:
        errors.append(f'Manifest mismatch: {entry["path"]}')

report = {
    'passed': not errors, 'reference_checks': checks,
    'manifest_files': len(manifest['files']),
    'packaged_bytes': sum(e['bytes'] for e in manifest['files']),
    'dictionary_entries': dict_entries, 'errors': errors,
    'scope': 'Static dependency, hash and source audit only; Android deployment/runtime not tested here.',
}
(REPO / 'docs/wanxiang-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
sys.exit(bool(errors))
