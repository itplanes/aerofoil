import json
import unittest

from app.cheats import CheatService, InvalidCheatIdentifier


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def iter_content(self, _size):
        yield json.dumps(self.payload).encode('utf-8')


class _Session:
    def __init__(self, payloads):
        self.payloads = list(payloads)

    def get(self, *_args, **_kwargs):
        return _Response(self.payloads.pop(0) if self.payloads else {}, 200)


class CheatServiceTests(unittest.TestCase):
    def test_requires_full_title_and_build_ids(self):
        service = CheatService(session=_Session([]))
        with self.assertRaises(InvalidCheatIdentifier):
            service.find_build('0100', 'ABCDEF0123456789')
        with self.assertRaises(InvalidCheatIdentifier):
            service.find_build('0100123412341234', '../bad')

    def test_merges_sources_and_deduplicates_content(self):
        payload = {'ABCDEF0123456789': {'Infinite value': '[Infinite value]\n04000000 00000000 00000001'}}
        service = CheatService(session=_Session([payload, payload, {}]), cache_ttl_s=60)
        result = service.find_build('0100123412341234', 'abcdef0123456789')
        self.assertEqual('exact', result['match'])
        self.assertEqual(1, len(result['cheats']))
        self.assertEqual('ABCDEF0123456789', result['build_id'])

    def test_render_only_accepts_known_selection_ids(self):
        payload = {'ABCDEF0123456789': {'Example': '[Example]\n04000000 00000000 00000001'}}
        service = CheatService(session=_Session([payload, {}, {}]), cache_ttl_s=60)
        found = service.find_build('0100123412341234', 'ABCDEF0123456789')
        rendered = service.render(
            found['title_id'],
            found['build_id'],
            [found['cheats'][0]['id'], 'unknown'],
        )
        self.assertTrue(rendered['content'].startswith('[Example]'))
        self.assertEqual(64, len(rendered['sha256']))


if __name__ == '__main__':
    unittest.main()
