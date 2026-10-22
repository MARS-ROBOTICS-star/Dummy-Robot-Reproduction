"""Validate the PBL document and source integrity, without running firmware."""

import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PLAN = ROOT / 'Dummy_V2项目驱动复刻方案_PBL版.md'
SUPPLEMENT = OUT / 'PBL路线复核补充.md'


def main():
    documents = []
    for path in [PLAN, SUPPLEMENT]:
        text = path.read_text(encoding='utf-8')
        assert len(re.findall(r'^```', text, re.M)) % 2 == 0, path.name
        missing_links = []
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if target.startswith(('http:', 'https:', '#')):
                continue
            if not (path.parent / unquote(target.split('#')[0])).exists():
                missing_links.append(target)
        missing_paths = []
        full_paths = set()
        for token in re.findall(r'`([^`\n]+)`', text):
            if re.match(r'^[1-6]\.(?:Hardware|Firmware|Software|Model|Bom|Docs)/', token):
                target = re.sub(r':\d.*$', '', token)
                full_paths.add(target)
                if not (ROOT / target).exists():
                    missing_paths.append(target)
        assert not missing_links, missing_links
        assert not missing_paths, missing_paths
        documents.append({'path': path.relative_to(ROOT).as_posix(),
                          'lines': len(text.splitlines()), 'characters': len(text),
                          'checked_full_paths': len(full_paths),
                          'missing_links': missing_links, 'missing_paths': missing_paths})

    text = PLAN.read_text(encoding='utf-8')
    headers = list(re.finditer(r'^### E(\d+)：([^\n]+)', text, re.M))
    assert [int(match[1]) for match in headers] == list(range(14))
    experiments = []
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        section = text[match.start():end]
        questions = re.findall(r'^\*\*([1-7])\. ', section, re.M)
        assert questions == list('1234567'), (match[0], questions)
        experiments.append({'experiment': 'E' + match[1], 'questions': len(questions)})

    used = set(re.findall(r'\[(S\d{2})\]', text))
    defined = set(re.findall(r'^\| (S\d{2}) \|', text, re.M))
    assert used <= defined, used - defined
    assert defined == {f'S{i:02d}' for i in range(1, 21)}
    fw = set(re.findall(r'^\| (FW\d{2}) ', text, re.M))
    assert fw == {f'FW{i:02d}' for i in range(1, 13)}
    assert all(f'| {category}：' in text for category in 'ABCDEF')
    assert all(f'| {number}. ' in text for number in range(1, 7))
    assert abs(256 / 51200 * 360 - 1.8) < 1e-12
    assert abs(1024 / 51200 - 0.02) < 1e-12
    assert abs(5120 / 51200 - 0.1) < 1e-12
    assert (1 << 7 | 0x23) == 0xA3 and (2 << 7 | 0x23) == 0x123

    with (OUT / 'file_inventory.csv').open(encoding='utf-8-sig', newline='') as source:
        baseline = list(csv.DictReader(source))
    checked = 0
    changed = []
    for row in baseline:
        if not re.match(r'^[1-6]\.', row['path']):
            continue
        path = ROOT / row['path']
        if not path.is_file():
            changed.append(row['path'])
            continue
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        checked += 1
        if digest != row['sha256']:
            changed.append(row['path'])
    assert not changed, changed
    report = {'documents': documents, 'experiments': experiments,
              'source_references': len(defined), 'staged_firmware_tasks': len(fw),
              'prerequisite_classes': 6, 'purchase_classes': 6,
              'original_artifacts_hash_checked': checked, 'changed_artifacts': changed,
              'arithmetic_checks': 'passed',
              'limitation': 'Document/static integrity checks only. No ARM build or hardware test.'}
    (OUT / 'pbl_document_checks.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
