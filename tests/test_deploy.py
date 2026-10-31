import tempfile
import unittest
import hashlib
from pathlib import Path

from deploy.build_release import download, source_files, validate_domain


class DeploymentPackageTests(unittest.TestCase):
    def test_domain_must_not_inject_proxy_configuration(self):
        for value in ['https://example.com', 'a.com\n:80 {', '../secrets', '*.example.com', '', '-bad.example.com']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_domain(value)

    def test_expected_domain_is_supported(self):
        self.assertEqual(validate_domain('btxm.sysplatsec.dev'), 'btxm.sysplatsec.dev')

    def test_vendor_sha512_checksums_are_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'vendor-source.bin'
            target = Path(tmp) / 'download.bin'
            source.write_bytes(b'verified vendor payload')
            expected = hashlib.sha512(source.read_bytes()).hexdigest()
            download(source.as_uri(), target, expected)
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_bad_vendor_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'vendor-source.bin'
            target = Path(tmp) / 'download.bin'
            source.write_bytes(b'wrong payload')
            with self.assertRaises(RuntimeError):
                download(source.as_uri(), target, '0' * 64)
            self.assertFalse(target.exists())

    def test_package_excludes_local_credentials_and_trading_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['run.py', '.env', '.env.example', 'data/trading.db', 'data/dashboard-token.txt',
                         'web/index.html', 'web/assets/font.ttf', 'bot/engine.py',
                         'bot/__pycache__/engine.pyc', '.qa/preview-data/dashboard-token.txt']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('sample')
            paths = {p.relative_to(root).as_posix() for p in source_files(root)}
            self.assertIn('run.py', paths)
            self.assertIn('web/assets/font.ttf', paths)
            self.assertNotIn('.env', paths)
            self.assertFalse(any(p.startswith(('data/', '.qa/')) or '__pycache__' in p for p in paths))


if __name__ == '__main__':
    unittest.main()
