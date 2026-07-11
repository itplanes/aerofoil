import json
import os
import shutil
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
    def test_list_builds_summarizes_tags(self):
        service = CheatService()
        service._load_title = lambda _title_id: {
            'builds': {
                '0123456789ABCDEF': [
                    {'tags': ['fps', 'graphics']},
                    {'tags': ['cheat']},
                ],
            },
            'provider_errors': [],
        }
        result = service.list_builds('0100000000000000')
        self.assertEqual(result['builds'][0]['cheat_count'], 2)
        self.assertEqual(result['builds'][0]['tag_counts']['fps'], 1)

    def test_render_all_builds_reports_conflicts(self):
        service = CheatService()
        service._load_title = lambda _title_id: {
            'builds': {'0123456789ABCDEF': [
                {'name': '30 FPS', 'content': '[30 FPS]\n1', 'conflict_groups': ['fps']},
                {'name': '60 FPS', 'content': '[60 FPS]\n2', 'conflict_groups': ['fps']},
            ]},
            'provider_errors': [],
        }
        result = service.render_all_builds('0100000000000000')
        self.assertEqual(result['builds'][0]['entry_count'], 2)
        self.assertEqual(result['builds'][0]['conflicts'][0]['group'], 'fps')

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

    def test_prefers_bundled_database_without_network(self):
        root = os.path.join('.tmp', 'test-cheatdb')
        shutil.rmtree(root, ignore_errors=True)
        os.makedirs(os.path.join(root, 'cheats'), exist_ok=True)
        title_id = '0100123412341234'
        build_id = 'ABCDEF0123456789'
        with open(os.path.join(root, 'cheats', f'{title_id}.json'), 'w', encoding='utf-8') as handle:
            json.dump({build_id: {'Bundled': '[Bundled]\n04000000 00000000 00000001'}}, handle)

        previous_dir = os.environ.get('AEROFOIL_CHEATS_DB_DIR')
        previous_fallback = os.environ.get('AEROFOIL_CHEATS_REMOTE_FALLBACK')
        os.environ['AEROFOIL_CHEATS_DB_DIR'] = root
        os.environ['AEROFOIL_CHEATS_REMOTE_FALLBACK'] = 'false'
        try:
            service = CheatService(session=_Session([]), cache_ttl_s=60)
            result = service.find_build(title_id, build_id)
            self.assertEqual('exact', result['match'])
            self.assertEqual('Bundled', result['cheats'][0]['name'])
        finally:
            if previous_dir is None:
                os.environ.pop('AEROFOIL_CHEATS_DB_DIR', None)
            else:
                os.environ['AEROFOIL_CHEATS_DB_DIR'] = previous_dir
            if previous_fallback is None:
                os.environ.pop('AEROFOIL_CHEATS_REMOTE_FALLBACK', None)
            else:
                os.environ['AEROFOIL_CHEATS_REMOTE_FALLBACK'] = previous_fallback
            shutil.rmtree(root, ignore_errors=True)

    def test_classifies_fps_resolution_and_graphics_names(self):
        service = CheatService(session=_Session([]))
        fps = service.classify('60 FPS Unlock')
        resolution = service.classify('Dynamic Resolution 1080p')
        graphics = service.classify('Disable Motion Blur and improve shadows')
        self.assertEqual(['fps'], fps['tags'])
        self.assertEqual(['fps'], fps['conflict_groups'])
        self.assertEqual(['resolution'], resolution['tags'])
        self.assertIn('resolution', resolution['conflict_groups'])
        self.assertEqual(['graphics'], graphics['tags'])
        self.assertIn('graphics:motion_blur', graphics['conflict_groups'])
        self.assertIn('graphics:shadows', graphics['conflict_groups'])

    def test_render_reports_mutually_exclusive_selections(self):
        payload = {
            'ABCDEF0123456789': {
                '30 FPS': '[30 FPS]\n04000000 00000000 0000001E',
                '60 FPS': '[60 FPS]\n04000000 00000000 0000003C',
            }
        }
        service = CheatService(session=_Session([payload, {}, {}]), cache_ttl_s=60)
        found = service.find_build('0100123412341234', 'ABCDEF0123456789')
        rendered = service.render(
            found['title_id'],
            found['build_id'],
            [item['id'] for item in found['cheats']],
        )
        self.assertEqual('fps', rendered['conflicts'][0]['group'])
        self.assertEqual(2, len(rendered['conflicts'][0]['entry_ids']))


if __name__ == '__main__':
    unittest.main()
