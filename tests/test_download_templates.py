import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DownloadTemplateRegressionTests(unittest.TestCase):
    def test_index_download_search_rows_use_safe_dom_construction(self):
        content = (REPO_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")

        self.assertIn("function buildDownloadSearchRow(item, actionLabel, extraData = {}) {", content)
        self.assertIn("const row = $('<tr></tr>');", content)
        self.assertIn("row.append($('<td></td>').text(item?.title || '-'));", content)
        self.assertIn("row.append($('<td></td>').text(item?.indexer || '-'));", content)
        self.assertIn("button.attr('data-download-url', String(item?.download_url || ''));", content)
        self.assertNotIn("return `<tr>${cells.join('')}</tr>`;", content)
        self.assertNotIn('data-download-url="${item.download_url || \'\'}"', content)

    def test_active_download_rows_use_safe_dom_construction(self):
        content = (REPO_ROOT / "app" / "templates" / "downloads.html").read_text(encoding="utf-8")

        self.assertIn("function loadActiveDownloads() {", content)
        self.assertIn("const row = $('<tr></tr>');", content)
        self.assertIn("row.append($('<td class=\"small\"></td>').text((item['name'] || '').toString()));", content)
        self.assertIn("row.append($('<td class=\"small text-muted\"></td>').text((item['status'] || '').toString()));", content)
        self.assertIn("body.append(row);", content)
        self.assertNotIn("const row = $(`<tr>${cells.join('')}</tr>`);", content)
        self.assertNotIn("`<td class=\"small\">${(item['name'] || '').toString()}</td>`", content)


if __name__ == "__main__":
    unittest.main()
