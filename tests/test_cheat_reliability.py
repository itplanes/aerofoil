import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from app.cheats import CheatService


TITLE = '0100123412341234'
BID = 'ABCDEF0123456789'


class ArchiveResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def iter_content(self, _size):
        yield self.content


class CheatReliabilityTests(unittest.TestCase):
    def setUp(self):
        os.makedirs('.tmp', exist_ok=True)
        self.root = tempfile.mkdtemp(prefix='cheat-reliability-', dir='.tmp')
        self.database = os.path.join(self.root, 'database')
        self.env = patch.dict(os.environ, {'AEROFOIL_CHEATS_DB_UPDATE_DIR': self.database,
                                          'AEROFOIL_CHEATS_DB_ARCHIVE_URL': 'https://example.invalid/database.zip'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def archive(self, extra=None):
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w') as archive:
            for name in ('cheats', 'cheats_gbatemp', 'cheats_gfx'):
                archive.writestr(f'snapshot/{name}/', '')
            archive.writestr(f'snapshot/cheats/{TITLE}.json', json.dumps({BID: {'Example code': '[Example code]\n04000000 00000000 00000001'}}))
            for name, value in extra or []:
                archive.writestr(name, value)
        return content.getvalue()

    def service(self, archive):
        session = type('Session', (), {'get': lambda _self, *_args, **_kwargs: ArchiveResponse(archive)})()
        return CheatService(session=session)

    def test_compatibility_requires_actual_bid_for_exact_state(self):
        self.assertEqual('exact', CheatService.compatibility(BID, 0, 0, BID))
        self.assertEqual('version_recommended', CheatService.compatibility(BID, 0, 0))
        self.assertEqual('unknown', CheatService.compatibility(BID, None, 0))
        self.assertEqual('incompatible', CheatService.compatibility(BID, 1, 1, '0000000000000000'))
        self.assertEqual('incompatible', CheatService.compatibility(BID, 2, 1))

    def test_index_never_contains_code_content(self):
        service = self.service(b'')
        service._load_title = lambda _id: {'builds': {BID: [{'tags': [], 'content': 'secret code'}]},
                                          'versions': {BID: 65536}, 'provider_errors': []}
        result = service.list_builds(TITLE, 65536)
        self.assertEqual('version_recommended', result['builds'][0]['compatibility'])
        self.assertNotIn('secret code', json.dumps(result))

    def test_success_records_archive_identity(self):
        service = self.service(self.archive())
        service.sync_database()
        status = service.get_sync_status()
        self.assertTrue(status['using_updated_database'])
        self.assertEqual(64, len(status['archive_sha256']))
        self.assertFalse(status['sync_running'])
        self.assertIsNone(status['last_error'])

    def test_swap_failure_restores_previous_generation(self):
        service = self.service(self.archive())
        service.sync_database()
        marker = os.path.join(self.database, 'previous-generation')
        with open(marker, 'w') as handle:
            handle.write('keep')
        replace = os.replace

        def fail_staging(source, target):
            if source == self.database + '.new':
                raise OSError('simulated swap failure')
            return replace(source, target)

        with patch('app.cheats.service.os.replace', side_effect=fail_staging):
            with self.assertRaisesRegex(OSError, 'swap failure'):
                service.sync_database()
        self.assertTrue(os.path.isfile(marker))
        self.assertIn('swap failure', service.get_sync_status()['last_error'])

    def test_rejects_zip_traversal_and_keeps_database(self):
        service = self.service(self.archive())
        service.sync_database()
        service._session = self.service(self.archive([('../escape.txt', 'bad')]))._session
        with self.assertRaisesRegex(ValueError, 'unsafe path'):
            service.sync_database()
        self.assertTrue(os.path.isdir(self.database))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'escape.txt')))

    def test_rejects_extraction_limit(self):
        with patch('app.cheats.service._MAX_EXTRACTED_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                self.service(self.archive()).sync_database()

    def test_roles_preserve_native_master_sections(self):
        self.assertEqual('master', CheatService.entry_role('Example', '{Master}\n04000000 00000000 00000001'))
        self.assertEqual('restore', CheatService.entry_role('Restore default FPS', '[Restore]\n04000000 00000000 00000001'))


if __name__ == '__main__':
    unittest.main()
