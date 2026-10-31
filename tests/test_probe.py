import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from probe_sources import inspect_html


class ProbeTests(unittest.TestCase):

    def test_detects_table_and_headers(self):
        html = """
        <html>
        <title>Test</title>
        <table>
            <tr>
                <th>回別</th>
                <th>抽せん日</th>
            </tr>
            <tr>
                <td>1</td>
                <td>2020-01-01</td>
            </tr>
        </table>
        </html>
        """.encode("utf-8")

        result = inspect_html(html)

        self.assertEqual(result["table_count"], 1)
        self.assertTrue(
            result["keyword_presence"]["回別"]
        )
        self.assertEqual(
            result["tables"][0]["row_count"], 2
        )

    def test_empty_page(self):
        html = b"<html><body>no table</body></html>"

        result = inspect_html(html)

        self.assertEqual(result["table_count"], 0)


if __name__ == "__main__":
    unittest.main()
