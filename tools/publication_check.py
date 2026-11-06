#!/usr/bin/env python3
"""Harmless regression checks for publication and delivery boundaries."""
import json
import tempfile
import zipfile
from pathlib import Path

from dev_check import check, run, write, REPO
from package_skill import package


def main():
    with tempfile.TemporaryDirectory(prefix='econ-publication-') as tmp:
        base = Path(tmp)
        root = check(base)
        # A registered but unused crop must stay out of both modes.
        u = json.loads((root / 'units/u001.json').read_text())
        with (root / 'content/b001.tex').open('a') as f:
            f.write('\n% \\includegraphics{assets/diagram.png}\n')
        (root / 'content/private.tex').write_text('PRIVATE-STUDY-ONLY')
        u['blocks'].append({'id': 'private001', 'kind': 'text', 'origin': 'explanation', 'refs': [],
                            'body': {'study': 'content/private.tex'}})
        u['issues'] = [{'id': 'private_note', 'severity': 'note', 'status': 'open',
                        'block_ids': ['private001'], 'summary': 'Private summary', 'detail': 'PRIVATE-DETAIL'}]
        write(root / 'units/u001.json', u)
        run('assemble', '--project', root, '--mode', 'faithful')
        dest = root / 'build/faithful'
        assert not (dest / 'assets/diagram.png').exists()
        mapping = (dest / 'source-map.json').read_text()
        assert 'PRIVATE-' not in mapping and 'private001' not in mapping and 'board.png' not in mapping
        # RC code can only write a harmless marker, which must never be created.
        marker = base / 'rc-executed'
        (dest / '.latexmkrc').write_text('open(my $f, ">", "%s"); print $f "unexpected"; close($f);\n' % marker)
        run('compile', '--project', root, '--mode', 'faithful')
        assert not marker.exists()
        fragment = root / 'content/b001.tex'
        clean_body = fragment.read_text()
        for command in (r'\includegraphics{assets/diagram.png}', r'\pgfimage{assets/diagram.png}'):
            fragment.write_text(clean_body + '\n' + command)
            result = run('assemble', '--project', root, '--mode', 'faithful', expected=2)
            assert 'issue.evidence_asset' in result['error']
        fragment.write_text(clean_body)
        outside = base / 'canary.tex'
        outside.write_text('OUTSIDE-CANARY')
        original = (root / 'content/b001.tex').read_text()
        for reference in (str(outside), '../../canary.tex'):
            (root / 'content/b001.tex').write_text(original + '\n\\input{' + reference + '}')
            outcome = run('assemble', '--project', root, '--mode', 'faithful', expected=2)
            assert 'unsupported' in outcome['error']
        (root / 'content/b001.tex').write_text(original)
        run('assemble', '--project', root, '--mode', 'faithful')
        run('compile', '--project', root, '--mode', 'faithful')
        packed = run('package', '--project', root, '--mode', 'faithful', '--allow-unreviewed', expected=3)
        with zipfile.ZipFile(packed['project_zip']) as z:
            assert not any(n.startswith('assets/') for n in z.namelist())
            assert 'PRIVATE-' not in z.read('source-map.json').decode()
        bundle = base / 'skill.zip'
        package(bundle)
        with zipfile.ZipFile(bundle) as z:
            assert z.read('advanced-econ-note2pdf/LICENSE') == (REPO / 'LICENSE').read_bytes()
    print('PASS: unused crops, mode/private metadata, RC disabled, absolute/parent TeX reads rejected, license bundled')


if __name__ == '__main__':
    main()
