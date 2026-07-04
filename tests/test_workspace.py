import tempfile
import unittest
from pathlib import Path

from uefn_mcp.workspace import VerseWorkspace, WorkspaceError, render_template, to_verse_identifier


class WorkspaceTests(unittest.TestCase):
    def test_identifier_cleanup(self):
        self.assertEqual(to_verse_identifier("My Device!"), "my_device")
        self.assertEqual(to_verse_identifier("123 Start"), "device_123_start")

    def test_template_render(self):
        content = render_template("basic_device", "Score Device")
        self.assertIn("score_device := class(creative_device)", content)
        self.assertIn("OnBegin<override>()", content)

    def test_write_read_and_list_verse_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Demo.uefnproject").write_text("{}", encoding="utf-8")
            workspace = VerseWorkspace.discover(root)
            written = workspace.write_verse_file("Verse/test_device.verse", "test := class():\n")
            self.assertTrue(Path(written["path"]).exists())
            read = workspace.read_verse_file("Verse/test_device.verse")
            self.assertEqual(read["content"], "test := class():\n")
            files = workspace.list_verse_files()
            self.assertEqual(len(files), 1)

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = VerseWorkspace(Path(tmp).resolve())
            with self.assertRaises(WorkspaceError):
                workspace.write_verse_file("../bad.verse", "")

    def test_create_device_defaults_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = VerseWorkspace(Path(tmp).resolve())
            workspace.create_device("Score Device")
            with self.assertRaises(WorkspaceError):
                workspace.create_device("Score Device")


if __name__ == "__main__":
    unittest.main()

