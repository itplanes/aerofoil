import os
import shutil
import tempfile
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from flask import Flask
from app.db import db, Libraries, Files, Titles, Apps
from app.constants import APP_TYPE_BASE
from app.library import organize_library, organize_files


class OrganizePreviewTests(unittest.TestCase):
    def setUp(self):
        os.makedirs('.tmp', exist_ok=True)
        self.root = os.path.abspath(tempfile.mkdtemp(prefix='organize-preview-', dir='.tmp'))
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.library = Libraries(path=self.root)
        title = Titles(title_id='0100123412341234')
        self.content = Apps(title=title, app_id=title.title_id, app_version='0', app_type=APP_TYPE_BASE, owned=True)
        db.session.add_all([self.library, self.content])
        db.session.commit()
        self.destination_dir = os.path.join(self.root, 'organized')
        self.destination_name = 'Example Title.nsp'
        self.patches = [
            patch('app.library.titles_lib.titledb_session', side_effect=lambda: nullcontext()),
            patch('app.library.titles_lib.get_game_info', return_value={'name': 'Example Title'}),
            patch('app.library._get_active_template', return_value={}),
            patch('app.library._build_destination', return_value=(self.destination_dir, self.destination_name)),
            patch('app.library._get_file_signature', return_value={'example-signature'}),
        ]
        for mock in self.patches:
            mock.start()

    def tearDown(self):
        for mock in reversed(self.patches):
            mock.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()
        shutil.rmtree(self.root, ignore_errors=True)

    def add_file(self, relative_path):
        path = os.path.join(self.root, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as handle:
            handle.write(b'example fixture content')
        entry = Files(library=self.library, filepath=path, filename=os.path.basename(path), extension='nsp', identified=True)
        db.session.add(entry)
        self.content.files.append(entry)
        db.session.commit()
        return path

    def test_duplicate_preview_does_not_delete_files_or_database_rows(self):
        source = self.add_file('incoming/Example.nsp')
        destination = self.add_file('organized/Example Title.nsp')
        result = organize_library(dry_run=True)
        self.assertTrue(result['success'])
        self.assertTrue(os.path.isfile(source))
        self.assertTrue(os.path.isfile(destination))
        self.assertEqual(2, Files.query.count())
        self.assertEqual('keep_existing_remove_duplicate', result['plan'][0]['action'])
        self.assertEqual(64, len(result['plan_digest']))

    def test_preview_reserves_distinct_destinations_and_detects_source_changes(self):
        source = self.add_file('incoming/Example A.nsp')
        self.add_file('incoming/Example B.nsp')
        before = organize_library(dry_run=True)
        self.assertEqual(2, len({item['destination'] for item in before['plan']}))
        self.assertTrue(before['plan'][1]['collision_renamed'])
        with open(source, 'ab') as handle:
            handle.write(b'changed')
        after = organize_library(dry_run=True)
        self.assertNotEqual(before['plan_digest'], after['plan_digest'])
        self.assertEqual(2, Files.query.count())

    def test_scoped_preview_also_keeps_duplicate_files(self):
        source = self.add_file('incoming/Example.nsp')
        destination = self.add_file('organized/Example Title.nsp')
        result = organize_files([source], dry_run=True)
        self.assertTrue(result['success'])
        self.assertTrue(os.path.isfile(source))
        self.assertTrue(os.path.isfile(destination))
        self.assertEqual(2, Files.query.count())


if __name__ == '__main__':
    unittest.main()
