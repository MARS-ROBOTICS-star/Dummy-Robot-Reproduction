"""Inventory source artifacts without executing or modifying them.

Run from any directory. The audit output directory itself is excluded.
PDF text and XLSX cells are convenience extracts, not authoritative CAD checks.
"""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def main():
    if '--verify' in sys.argv:
        with (OUT / 'file_inventory.csv').open(encoding='utf-8-sig', newline='') as source:
            baseline = list(csv.DictReader(source))
        changed = []
        missing = []
        for item in baseline:
            path = ROOT / item['path']
            if not path.is_file():
                missing.append(item['path'])
                continue
            with path.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            if digest != item['sha256']:
                changed.append(item['path'])
        known = {item['path'] for item in baseline}
        added = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                       if p.is_file() and OUT not in p.parents
                       and p.relative_to(ROOT).as_posix() not in known)
        print(json.dumps({'baseline_files': len(baseline), 'changed': changed,
                          'missing': missing, 'added_outside_audit': added}, ensure_ascii=False, indent=2))
        return
    extracts = OUT / 'extracted'
    extracts.mkdir(exist_ok=True)
    paths = sorted(p for p in ROOT.rglob('*') if p.is_file() and OUT not in p.parents)
    counts = Counter()
    sizes = Counter()
    duplicates = defaultdict(list)
    archives = []
    errors = []
    with (OUT / 'file_inventory.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(['path', 'bytes', 'sha256', 'extension', 'coverage'])
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            size = path.stat().st_size
            with path.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            section = relative.split('/')[0] if '/' in relative else '(root)'
            counts[section] += 1
            sizes[section] += size
            duplicates[digest].append(relative)
            writer.writerow([relative, size, digest, path.suffix.lower(), 'inventory_only'])
            if path.suffix.lower() in {'.zip', '.xlsx'}:
                try:
                    with zipfile.ZipFile(path) as archive:
                        archives.append({'path': relative, 'members': [
                            {'name': x.filename, 'bytes': x.file_size, 'crc': x.CRC}
                            for x in archive.infolist()]})
                        if path.suffix.lower() == '.xlsx':
                            strings = []
                            if 'xl/sharedStrings.xml' in archive.namelist():
                                tree = ET.fromstring(archive.read('xl/sharedStrings.xml'))
                                strings = [''.join(t.itertext()) for t in tree]
                            book = ET.fromstring(archive.read('xl/workbook.xml'))
                            rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
                            targets = {r.attrib['Id']: r.attrib['Target'] for r in rels}
                            sheets = []
                            for sheet in book.find('s:sheets', NS):
                                rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                                target = targets[rid]
                                target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
                                tree = ET.fromstring(archive.read(target))
                                rows = []
                                for row in tree.findall('.//s:sheetData/s:row', NS):
                                    cells = {}
                                    for cell in row.findall('s:c', NS):
                                        val = cell.find('s:v', NS)
                                        text = val.text if val is not None else ''
                                        if cell.attrib.get('t') == 's' and text:
                                            text = strings[int(text)]
                                        elif cell.attrib.get('t') == 'inlineStr':
                                            text = ''.join(cell.find('s:is', NS).itertext())
                                        formula = cell.find('s:f', NS)
                                        if formula is not None:
                                            text = {'formula': formula.text, 'cached': text}
                                        if text:
                                            cells[cell.attrib['r']] = text
                                    if cells:
                                        rows.append(cells)
                                sheets.append({'sheet': sheet.attrib['name'], 'rows': rows})
                            (extracts / (path.stem + '.json')).write_text(
                                json.dumps({'source': relative, 'sheets': sheets}, ensure_ascii=False, indent=2), encoding='utf-8')
                except (zipfile.BadZipFile, KeyError, ET.ParseError) as error:
                    errors.append({'path': relative, 'error': str(error)})
            if path.suffix.lower() == '.pdf' and shutil.which('pdftotext'):
                dest = extracts / (relative.replace('/', '__') + '.txt')
                proc = subprocess.run(['pdftotext', '-layout', str(path), str(dest)], capture_output=True, timeout=60)
                if proc.returncode:
                    errors.append({'path': relative, 'error': proc.stderr.decode(errors='replace')})
    summary = {
        'scope': str(ROOT), 'excluded': str(OUT.relative_to(ROOT)),
        'file_count': len(paths), 'bytes': sum(sizes.values()),
        'sections': {s: {'files': counts[s], 'bytes': sizes[s]} for s in sorted(counts)},
        'empty_files': [p.relative_to(ROOT).as_posix() for p in paths if p.stat().st_size == 0],
        'duplicate_groups': [items for items in duplicates.values() if len(items) > 1],
        'errors': errors,
    }
    (OUT / 'inventory_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'archive_members.json').write_text(json.dumps(archives, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'duplicate_groups'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
