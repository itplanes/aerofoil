import unittest

from app.settings import _normalize_shop_settings, verify_settings


class ShopSettingsValidationTests(unittest.TestCase):
    def test_legacy_encryption_is_always_disabled(self):
        normalized = _normalize_shop_settings({
            'encrypt': False,
            'tinfoil_only_mode': True,
        })
        self.assertTrue(normalized['tinfoil_only_mode'])
        self.assertFalse(normalized['encrypt'])

    def test_verify_shop_settings_ignores_legacy_encryption_fields(self):
        success, errors = verify_settings('shop', {
            'encrypt': True,
            'public_key': 'not-a-valid-pem',
        })
        self.assertTrue(success)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
