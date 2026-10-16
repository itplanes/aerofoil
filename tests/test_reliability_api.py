import unittest
from unittest.mock import patch
from app.app import app, _cheat_index_response, manage_organize_library, sync_cheat_database


class ReliabilityApiTests(unittest.TestCase):
    def test_index_rejects_invalid_internal_version_without_calling_provider(self):
        with patch('app.app.cheat_service.list_builds') as provider:
            with app.test_request_context('/?installed_version=-1'):
                response, status = _cheat_index_response('0100123412341234')
            self.assertEqual(400, status)
            provider.assert_not_called()

    def test_index_passes_device_evidence(self):
        with patch('app.app.cheat_service.list_builds', return_value={'builds': []}) as provider:
            with app.test_request_context('/?installed_version=0&actual_build_id=ABCDEF0123456789'):
                self.assertEqual([], _cheat_index_response('0100123412341234').get_json()['builds'])
            provider.assert_called_once_with('0100123412341234', 0, 'ABCDEF0123456789')

    def test_changed_plan_never_executes_organization(self):
        preview = {'success': True, 'plan_digest': 'new', 'plan': []}
        with patch('app.app.organize_library', return_value=preview) as organize:
            with app.test_request_context('/api/manage/organize', method='POST', json={'dry_run': False, 'plan_digest': 'old'}):
                _response, status = manage_organize_library.__wrapped__()
            self.assertEqual(409, status)
            organize.assert_called_once_with(dry_run=True, verbose=False)

    def test_approved_plan_executes_and_refreshes_library(self):
        with patch('app.app.organize_library', side_effect=[{'success': True, 'plan_digest': 'same'}, {'success': True}]) as organize:
            with patch('app.app.post_library_change') as refresh:
                with app.test_request_context('/api/manage/organize', method='POST', json={'dry_run': False, 'plan_digest': 'same'}):
                    self.assertTrue(manage_organize_library.__wrapped__().get_json()['success'])
                refresh.assert_called_once()
            self.assertEqual(2, organize.call_count)

    def test_manual_sync_returns_background_job_status(self):
        with patch('app.app.cheat_service.start_sync', return_value={'sync_running': True}) as start:
            with app.test_request_context('/api/cheats/database/sync', method='POST'):
                response, status = sync_cheat_database.__wrapped__()
            self.assertEqual(202, status)
            self.assertTrue(response.get_json()['sync_running'])
            start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
