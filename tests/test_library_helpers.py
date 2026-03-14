import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

_IMPORT_ERROR = None
try:
    from app.library import (
        _build_staging_output_path,
        _cleanup_import_staging_roots,
        _finalize_staged_conversion_output,
        _format_nsz_command,
        _pending_cleanup_roots,
        _pending_organize_paths,
        _sanitize_component,
        enqueue_cleanup_roots,
        enqueue_organize_paths,
    )
except ModuleNotFoundError as exc:
    _IMPORT_ERROR = exc


class LibraryHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if _IMPORT_ERROR is not None:
            raise unittest.SkipTest(f"Missing dependency for library helper tests: {_IMPORT_ERROR}")

    def test_sanitize_component(self):
        self.assertEqual(_sanitize_component('Game: Name?'), 'Game Name')
        self.assertEqual(_sanitize_component(''), 'Unknown')

    def test_format_nsz_command_threads(self):
        command = _format_nsz_command(
            '{nsz_runner} -C -o "{output_dir}" "{input_file}"',
            'C:\\input.nsp',
            'C:\\output.nsz',
            threads=4
        )
        self.assertIn('-t 4', command)
        self.assertIn('input.nsp', command)

    def test_build_staging_output_path_disabled_returns_final_output(self):
        source = '/library/Game.nsp'
        output = '/library/Game.nsz'
        self.assertEqual(_build_staging_output_path(source, output, ''), output)

    def test_build_staging_output_path_uses_staging_root(self):
        source = '/library/Game.nsp'
        output = '/library/Game.nsz'
        staging = '/tmp/aerofoil-stage'
        staged_output = _build_staging_output_path(source, output, staging)
        self.assertTrue(staged_output.startswith(staging + os.sep))
        self.assertEqual(os.path.basename(staged_output), 'Game.nsz')

    def test_finalize_staged_conversion_output_moves_file_to_source_directory(self):
        tmp_root = tempfile.mkdtemp(prefix='aerofoil_finalize_')
        self.addCleanup(shutil.rmtree, tmp_root, ignore_errors=True)

        library_dir = os.path.join(tmp_root, 'library')
        staging_root = os.path.join(tmp_root, 'staging')
        os.makedirs(library_dir, exist_ok=True)
        os.makedirs(staging_root, exist_ok=True)

        source_path = os.path.join(library_dir, 'Sample.nsp')
        staged_dir = os.path.join(staging_root, 'run-1')
        os.makedirs(staged_dir, exist_ok=True)
        staged_output = os.path.join(staged_dir, 'Sample.nsz')
        with open(staged_output, 'wb') as handle:
            handle.write(b'nsz-output')

        final_output = _finalize_staged_conversion_output(
            source_path=source_path,
            staged_output_path=staged_output,
            staging_root=staging_root,
        )

        self.assertEqual(final_output, os.path.join(library_dir, 'Sample.nsz'))
        self.assertTrue(os.path.exists(final_output))
        self.assertFalse(os.path.exists(staged_output))

    def test_finalize_staged_conversion_output_fails_if_final_exists(self):
        tmp_root = tempfile.mkdtemp(prefix='aerofoil_finalize_exists_')
        self.addCleanup(shutil.rmtree, tmp_root, ignore_errors=True)

        library_dir = os.path.join(tmp_root, 'library')
        staging_root = os.path.join(tmp_root, 'staging')
        os.makedirs(library_dir, exist_ok=True)
        os.makedirs(staging_root, exist_ok=True)

        source_path = os.path.join(library_dir, 'Sample.nsp')
        existing_final = os.path.join(library_dir, 'Sample.nsz')
        with open(existing_final, 'wb') as handle:
            handle.write(b'existing')

        staged_output = os.path.join(staging_root, 'Sample.nsz')
        with open(staged_output, 'wb') as handle:
            handle.write(b'new-output')

        with self.assertRaises(FileExistsError):
            _finalize_staged_conversion_output(
                source_path=source_path,
                staged_output_path=staged_output,
                staging_root=staging_root,
            )

    @patch("app.library.os.walk")
    @patch("app.library.os.path.isdir", return_value=True)
    @patch("app.library.os.path.isfile", return_value=False)
    def test_enqueue_organize_paths_expands_directories_to_files(self, isfile_mock, isdir_mock, walk_mock):
        walk_mock.return_value = [
            ("X:\\fixture-root\\Example Release NSW-GRP", [], ["game.nsp", "readme.nfo"]),
            ("X:\\fixture-root\\Example Release NSW-GRP\\subdir", [], ["dlc.nsp"]),
        ]
        _pending_organize_paths.clear()
        try:
            enqueue_organize_paths(["X:\\fixture-root\\Example Release NSW-GRP"])
            self.assertEqual(_pending_organize_paths, {
                "X:\\fixture-root\\Example Release NSW-GRP\\game.nsp",
                "X:\\fixture-root\\Example Release NSW-GRP\\readme.nfo",
                "X:\\fixture-root\\Example Release NSW-GRP\\subdir\\dlc.nsp",
            })
        finally:
            _pending_organize_paths.clear()

    @patch("app.library.os.path.isdir", return_value=True)
    def test_enqueue_cleanup_roots_tracks_only_directories(self, isdir_mock):
        _pending_cleanup_roots.clear()
        try:
            enqueue_cleanup_roots(["X:\\fixture-root\\Example Release NSW-GRP"])
            self.assertEqual(_pending_cleanup_roots, {"X:\\fixture-root\\Example Release NSW-GRP"})
        finally:
            _pending_cleanup_roots.clear()

    @patch("app.library.os.rmdir")
    @patch("app.library.os.listdir", return_value=[])
    @patch("app.library.os.remove")
    @patch("app.library.os.walk")
    @patch("app.library.os.path.isdir", return_value=True)
    def test_cleanup_import_staging_roots_removes_only_unsupported_leftovers(
        self,
        isdir_mock,
        walk_mock,
        remove_mock,
        listdir_mock,
        rmdir_mock,
    ):
        walk_mock.return_value = [
            ("X:\\fixture-root\\Example Release NSW-GRP\\subdir", [], ["keep.nsp", "proof.nfo"]),
            ("X:\\fixture-root\\Example Release NSW-GRP", ["subdir"], ["notes.txt"]),
        ]

        _cleanup_import_staging_roots(["X:\\fixture-root\\Example Release NSW-GRP"])

        self.assertEqual(
            [call.args[0] for call in remove_mock.call_args_list],
            [
                "X:\\fixture-root\\Example Release NSW-GRP\\subdir\\proof.nfo",
                "X:\\fixture-root\\Example Release NSW-GRP\\notes.txt",
            ],
        )


if __name__ == '__main__':
    unittest.main()
