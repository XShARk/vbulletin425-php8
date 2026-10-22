#!/usr/bin/env python3
"""Check the explicit public-file allowlist before creating or publishing a release."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
ALLOW={
 '.gitignore','.github/workflows/tests.yml','vb425_php8.py',
 'php/worker.php','php/transformer.php','php/runtime.php','profiles/4.2.5.json',
 'README.md','README.fr.md','LICENSE','NOTICE','CONTRIBUTING.md','SECURITY.md',
 'docs/LIMITATIONS.md','docs/VALIDATION.md','tests/test_patcher.py','tests/runtime.php',
 'tools/check_release.py','tools/package_release.py',
}
EXCLUDED={'.git','__pycache__','dist'}
PATTERNS={
 'vendor_license_identifier':rb'\bLE[0-9A-F]{8,}\b',
 'vendor_file_banner':rb'vBulletin Solutions Inc\. All Rights Reserved',
 'private_windows_location':rb'(?i)[a-z]:[\\/](?:Users[\\/]|xampp[\\/]|web84[\\/]|ACBackup[\\/])',
 'private_key':rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',
 'github_token':rb'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',
 'webhook_token':rb'https?://(?:discord(?:app)?\.com|media\.guilded\.gg)/[^\s\"\']*webhooks/',
}
def check():
    found=set();errors=[]
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(part in EXCLUDED for part in rel.parts):continue
        name=rel.as_posix();found.add(name)
        if p.is_symlink():errors.append(name+':symlink')
        if name not in ALLOW:errors.append(name+':not_in_public_allowlist');continue
        raw=p.read_bytes()
        for label,pattern in PATTERNS.items():
            if re.search(pattern,raw):errors.append(name+':'+label)
    for name in ALLOW-found:errors.append(name+':missing')
    profile=json.loads((ROOT/'profiles/4.2.5.json').read_text())
    for name,row in profile['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:errors.append('unsafe profile path')
        if set(row)!={'stock_sha256','patched_sha256'}:errors.append('unexpected profile data')
        if not all(re.fullmatch('[0-9a-f]{64}',value) for value in row.values()):errors.append('invalid fingerprint')
    return errors
if __name__=='__main__':
    errors=check();print(json.dumps({'public_files':len(ALLOW),'passed':not errors,'errors':errors},indent=2));sys.exit(bool(errors))
