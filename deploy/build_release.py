"""Build a credential-free Windows VPS installer, with offline Python wheels.

Does not connect to or change the VPS. Downloads vendor files over HTTPS only.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.deploy-cache'
PYTHON_VERSION = '3.13.17'
PYTHON_SHA256 = '5da012101ba2e17113a9a1cd901e9ce1441086f2b7ecb5de06ec94163899a190'
MT5_VERSION = '5.0.6231'
CADDY_VERSION = '2.11.7'


def validate_domain(value):
    if not isinstance(value, str) or len(value) > 253 or not re.fullmatch(
        r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', value
    ):
        raise ValueError('Domain must be a plain lowercase DNS hostname')
    return value


def source_files(root):
    # Explicit allowlist: never package data/, local .env, QA state or account credentials.
    exact = ['run.py', '.env.example', 'start.ps1', 'install-mt5.ps1', 'README.md', 'VPS-HANDOFF.md',
             'INSTALL-VPS.cmd', 'deploy/install-vps.ps1', 'deploy/run-worker.ps1',
             'docs/VPS-INSTALL-TH.md', 'docs/SETUP-TH.md']
    result = [root / p for p in exact if (root / p).is_file()]
    for directory in ['bot', 'web', 'docs/licenses']:
        for p in sorted((root / directory).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                result.append(p)
    return result


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def download(url, target, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    algorithm = 'sha512' if expected and len(expected) == 128 else 'sha256'
    if target.exists() and (not expected or digest(target, algorithm) == expected):
        return target
    req = urllib.request.Request(url, headers={'User-Agent': 'TradingDesk-Installer/1.0'})
    temporary = target.with_suffix(target.suffix + '.partial')
    with urllib.request.urlopen(req, timeout=60) as response, temporary.open('wb') as output:
        shutil.copyfileobj(response, output)
    if expected and digest(temporary, algorithm) != expected:
        raise RuntimeError(f'Vendor {algorithm} mismatch: {target.name}')
    temporary.replace(target)
    print('Downloaded', target.name, flush=True)
    return target


def build(domain, with_vendor=True):
    domain = validate_domain(domain)
    CACHE.mkdir(exist_ok=True)
    vendor = {}
    if with_vendor:
        py = download(f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-amd64.exe',
                      CACHE / 'python-amd64.exe', PYTHON_SHA256)
        vendor['vendor/python-amd64.exe'] = py
        caddy_root = f'https://github.com/caddyserver/caddy/releases/download/v{CADDY_VERSION}'
        checksums = download(f'{caddy_root}/caddy_{CADDY_VERSION}_checksums.txt', CACHE / 'caddy-checksums.txt')
        filename = f'caddy_{CADDY_VERSION}_windows_amd64.zip'
        line = next(line for line in checksums.read_text().splitlines() if line.split()[-1].lstrip('*') == filename)
        archive = download(f'{caddy_root}/{filename}', CACHE / filename, line.split()[0])
        with zipfile.ZipFile(archive) as z:
            (CACHE / 'caddy.exe').write_bytes(z.read('caddy.exe'))
            (CACHE / 'caddy-LICENSE').write_bytes(z.read('LICENSE'))
        vendor['vendor/caddy.exe'] = CACHE / 'caddy.exe'
        vendor['vendor/caddy-LICENSE'] = CACHE / 'caddy-LICENSE'
        # Official Windows download linked by metatrader5.com/en/download.
        mt5 = download('https://download.terminal.free/cdn/web/metaquotes.ltd/mt5/mt5setup.exe', CACHE / 'mt5setup.exe')
        vendor['vendor/mt5setup.exe'] = mt5
        wheels = CACHE / 'wheels'
        wheels.mkdir(exist_ok=True)
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--disable-pip-version-check',
                        '--dest', str(wheels), '--only-binary=:all:', '--platform', 'win_amd64',
                        '--implementation', 'cp', '--python-version', '3.13', '--abi', 'cp313',
                        f'MetaTrader5=={MT5_VERSION}'], check=True)
        # Include only the chosen MT5 wheel and its newest matching numpy wheel;
        # cached obsolete versions must not be installed accidentally.
        chosen = sorted(wheels.glob(f'metatrader5-{MT5_VERSION}-*.whl'))
        numpy = sorted(wheels.glob('numpy-*.whl'), key=lambda p: p.stat().st_mtime)
        if len(chosen) != 1 or not numpy:
            raise RuntimeError('Missing expected Windows Python wheels')
        for wheel in [*chosen, numpy[-1]]:
            vendor['vendor/wheels/' + wheel.name] = wheel
    package = ROOT / 'dist' / 'TradingDesk-Windows-VPS.zip'
    package.parent.mkdir(exist_ok=True)
    metadata = {'domain': domain, 'port': 8899, 'python': PYTHON_VERSION,
                'metatrader5': MT5_VERSION, 'caddy': CADDY_VERSION,
                'default_install_root': 'C:\\Trading-bot', 'offline_vendor_files': with_vendor}
    files = {p.relative_to(ROOT).as_posix(): p for p in source_files(ROOT)}
    files.update(vendor)
    manifest = {name: digest(p) for name, p in files.items()}
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, p in sorted(files.items()):
            z.write(p, name)
        z.writestr('deploy/package.json', json.dumps(metadata, indent=2))
        z.writestr('deploy/SHA256.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(package) as z:
        if z.testzip() is not None:
            raise RuntimeError('Release archive verification failed')
    package.with_suffix('.zip.sha256').write_text(digest(package) + '  ' + package.name + '\n')
    print(f'Built {package.name}: {package.stat().st_size / 1024 / 1024:.1f} MiB, {len(files)} files', flush=True)
    return package


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', default='btxm.sysplatsec.dev')
    parser.add_argument('--source-only', action='store_true', help='Verification package; cannot install without vendor files')
    args = parser.parse_args()
    build(args.domain, not args.source_only)
