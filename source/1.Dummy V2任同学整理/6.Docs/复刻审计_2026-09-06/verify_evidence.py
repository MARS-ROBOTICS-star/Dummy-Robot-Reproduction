"""Recheck selected audit claims; never execute project applications or firmware."""

import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote
import zipfile


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
MOTOR = ROOT / '2.Firmware/dummy-42motor-fw'


def main():
    result = {'tools': {name: shutil.which(name) for name in [
        'cmake', 'arm-none-eabi-gcc', 'make', 'ninja', 'gcc', 'g++', 'pdftotext']}}
    with (OUT / 'file_inventory.csv').open(encoding='utf-8-sig', newline='') as source:
        inventory = list(csv.DictReader(source))
    stubs = []
    for row in inventory:
        path = ROOT / row['path']
        if 0 < int(row['bytes']) < 250 and path.suffix in {'.c', '.h', '.cpp', '.js'}:
            text = path.read_text(errors='replace').strip()
            if re.fullmatch(r'(?:\.\./)+[^\s]+', text):
                stubs.append({'path': row['path'], 'text': text, 'is_symlink': path.is_symlink(),
                              'target_exists': (path.parent / text).exists()})
    result['relative_path_source_stubs'] = stubs
    includes = ['Core/Inc', 'Drivers/STM32F1xx_HAL_Driver/Inc',
                'Drivers/STM32F1xx_HAL_Driver/Inc/Legacy',
                'Drivers/CMSIS/Device/ST/STM32F1xx/Include', 'Drivers/CMSIS/Include']
    if shutil.which('gcc'):
        command = ['gcc', '-E', '-dM', '-DUSE_HAL_DRIVER', '-DSTM32F103xB',
                   *['-I' + str(MOTOR / p) for p in includes], str(MOTOR / 'Core/Src/system_stm32f1xx.c')]
        proc = subprocess.run(command, capture_output=True, text=True)
        result['host_preprocessor'] = {
            'command': command, 'exit': proc.returncode,
            'hse_macro': re.findall(r'^#define HSE_VALUE .+$', proc.stdout, re.M),
            'stderr': proc.stderr,
            'limitation': 'Host preprocessing only; not an ARM firmware build.',
        }
        assert proc.returncode == 0
        assert result['host_preprocessor']['hse_macro'] == ['#define HSE_VALUE 12000000U']
    if shutil.which('g++'):
        source = '''constexpr bool check() {
          for (unsigned node = 0; node < 16; ++node)
            if ((node >= 1 & node <= 6) != (node >= 1 && node <= 6)) return false;
          return true;
        }
        static_assert(check());
        '''
        proc = subprocess.run(['g++', '-std=c++17', '-x', 'c++', '-fsyntax-only', '-'],
                              input=source, capture_output=True, text=True)
        result['cpp_boolean_range_check'] = {'exit': proc.returncode, 'stderr': proc.stderr}
        assert proc.returncode == 0
    archives = []
    for path in sorted((ROOT / '1.Hardware').rglob('*.zip')):
        if 'gaber' not in path.name.lower() and 'gerber' not in path.name.lower():
            continue
        with zipfile.ZipFile(path) as archive:
            text_members = {name: archive.read(name).decode(errors='replace')
                            for name in archive.namelist() if not name.endswith('/')}
            archives.append({
                'path': path.relative_to(ROOT).as_posix(), 'files': len(text_members),
                'zip_crc_error': archive.testzip(),
                'nc_drill_candidates': [name for name, text in text_members.items()
                                        if re.search(r'(?m)^M48\b', text)],
                'rules_file_prefix': {name: text[:200] for name, text in text_members.items()
                                      if name.lower().endswith('.rul')},
            })
    result['gerber_packages'] = archives
    source = (ROOT / '2.Firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp').read_text()
    result['ref_constructor_rows'] = re.findall(r'^\s*motorJ\[[1-6]\] =.*$', source, re.M)
    base = {x['path']: x['sha256'] for x in inventory}
    differences = []
    prefix = '2.Firmware/dummy-42motor-fw/'
    for path, digest in base.items():
        if path.startswith(prefix):
            relative = path[len(prefix):]
            other = '2.Firmware/dummy-35motor-fw/' + relative
            if base.get(other) != digest:
                differences.append({'path_42': path, 'path_35_exists': other in base})
    result['motor_42_vs_35_hash_differences'] = differences
    parses = []
    for folder in ['3.Software/simple-cli', '3.Software/CLI-Tool']:
        for path in sorted((ROOT / folder).rglob('*.py')):
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            except (SyntaxError, UnicodeError) as error:
                parses.append({'path': path.relative_to(ROOT).as_posix(), 'error': str(error)})
    result['python_ast_errors'] = parses
    result['budget_interval_sums_CNY'] = {
        'required_tools': [sum([300, 80, 50, 20, 80]), sum([700, 200, 200, 60, 200])],
        'single_axis': [sum([150, 80, 20, 30, 30]), sum([600, 250, 100, 150, 100])],
    }
    documents = [ROOT / 'Dummy_V2详细复刻方案_审计修订版.md',
                 OUT / '审计结论与证据.md', OUT / '实施记录模板.md',
                 ROOT / 'Dummy_V2复刻与学习方案_初稿.md']
    doc_checks = []
    for path in documents:
        text = path.read_text()
        assert len(re.findall(r'^```', text, re.M)) % 2 == 0, str(path)
        broken_links = []
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if target.startswith(('http:', 'https:', '#')):
                continue
            target = unquote(target.split('#')[0])
            if not (path.parent / target).exists():
                broken_links.append(target)
        assert not broken_links, broken_links
        missing_paths = []
        if path != documents[-1]:
            for token in re.findall(r'`([^`\n]+)`', text):
                if re.match(r'^[1-6]\.(?:Hardware|Firmware|Software|Model|Bom|Docs)/', token):
                    target = re.sub(r':\d.*$', '', token)
                    if not (ROOT / target).exists():
                        missing_paths.append(target)
            assert not missing_paths, missing_paths
        doc_checks.append({'path': path.relative_to(ROOT).as_posix(),
                           'lines': len(text.splitlines()), 'characters': len(text),
                           'broken_links': broken_links, 'missing_source_paths': missing_paths})
    plan = documents[0].read_text()
    assert set(re.findall(r'^\| (T\d{2}) \|', plan, re.M)) == {f'T{i:02d}' for i in range(1, 35)}
    assert set(re.findall(r'^\| (FW\d{2}) \|', plan, re.M)) == {f'FW{i:02d}' for i in range(1, 13)}
    assert set(re.findall(r'^\| (D\d{2}) \|', plan, re.M)) == {f'D{i:02d}' for i in range(1, 21)}
    assert set(re.findall(r'^\| (G\d) \|', plan, re.M)) == {f'G{i}' for i in range(8)}
    for path in OUT.glob('deepseek_*.md'):
        assert path.read_text().startswith('> 原始子代理意见'), str(path)
    agent_runs = json.loads((OUT / 'agent_runs.json').read_text())
    assert len(agent_runs) == 5
    assert all(x['complete'] and x['exit'] == '0'
               and x['models'] == ['opencode-go/deepseek-v4-pro'] for x in agent_runs)
    changed = []
    for row in inventory:
        path = ROOT / row['path']
        assert path.is_file(), row['path']
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if digest != row['sha256']:
            changed.append(row['path'])
    assert changed == ['Dummy_V2复刻与学习方案_初稿.md'], changed
    result['delivery_checks'] = {'documents': doc_checks, 'test_cases': 34,
                                 'firmware_tasks': 12, 'work_units': 20, 'gates': 8,
                                 'verified_pro_sessions': 5, 'changed_baseline_files': changed}
    (OUT / 'evidence_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {key: value for key, value in result.items()
               if key not in {'relative_path_source_stubs', 'motor_42_vs_35_hash_differences'}}
    summary['source_stub_count'] = len(stubs)
    summary['motor_hash_difference_count'] = len(differences)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
