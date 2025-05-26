import datetime
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

# this allows imports from the modules folder to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import sqlite_helpers


class TestDatabaseSetup(unittest.TestCase):
    EXAMPLE_DATETIME = datetime.datetime(1996, 12, 24, 12, 0, 0)
    EXAMPLE_URL = "https://sce.sjsu.edu/"

    def test_maybe_create_table(self):
        with tempfile.NamedTemporaryFile() as tmp:
            result = sqlite_helpers.maybe_create_table(tmp.name)
            self.assertTrue(result)

            db = sqlite3.connect(tmp.name)
            cursor = db.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='urls';"
            )
            # get first element in response, cursor.fetchone() returns ('urls',)
            [table] = cursor.fetchone()
            self.assertEqual(table, "urls")

    @mock.patch("sqlite3.connect")
    def test_maybe_create_table_handles_exception(self, mock_connect):
        # Mock connection and cursor
        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_cursor.execute.side_effect = Exception("Simulated execute error")

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        with tempfile.NamedTemporaryFile() as tmp:
            result = sqlite_helpers.maybe_create_table(tmp.name)
        self.assertFalse(result)

    @mock.patch("modules.sqlite_helpers.datetime")
    def test_insert_url(self, mock_datetime):
        mock_datetime.fromisoformat.return_value = self.EXAMPLE_DATETIME
        mock_datetime.now.return_value = self.EXAMPLE_DATETIME
        cases = [
            ("does not set expiration date if it is None", None),
            ("sets expiration date if it is passed in", self.EXAMPLE_DATETIME),
        ]

        for test_name, expiration_value in cases:
            with self.subTest(test_name=test_name, expiration_value=expiration_value):
                with tempfile.NamedTemporaryFile() as tmp:
                    sqlite_helpers.maybe_create_table(tmp.name)
                    result = sqlite_helpers.insert_url(
                        tmp.name, self.EXAMPLE_URL, "home", expiration_value
                    )
                    self.assertEqual(result, self.EXAMPLE_DATETIME)

                    db = sqlite3.connect(tmp.name)
                    cursor = db.cursor()
                    cursor.execute("SELECT * FROM urls;")

                    [
                        row_id,
                        url,
                        alias,
                        created_at,
                        used,
                        expires_at,
                    ] = cursor.fetchone()
                    self.assertEqual(row_id, 1)
                    self.assertEqual(url, self.EXAMPLE_URL)
                    self.assertEqual(alias, "home")
                    self.assertEqual(created_at, "1996-12-24 12:00:00")
                    self.assertEqual(used, 1)
                    if expiration_value is None:
                        self.assertIsNone(expires_at)
                    else:
                        self.assertEqual(expires_at, "1996-12-24 12:00:00")

    def test_insert_url_duplicate_alias_not_allowed(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            result = sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, "home")
            self.assertIsNotNone(result)
            result_duplicate_alias = sqlite_helpers.insert_url(
                tmp.name, self.EXAMPLE_URL, "home"
            )
            self.assertIsNone(result_duplicate_alias)

    def test_get_urls(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            result = sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, "home")
            self.assertIsNotNone(result, self.EXAMPLE_DATETIME)
            result_duplicate_alias = sqlite_helpers.insert_url(
                tmp.name, self.EXAMPLE_URL, "home"
            )
            self.assertIsNone(result_duplicate_alias)

    def test_get_urls_page(self):
        cases = [
            # the first url should be the most recently created one
            # with alias url_29
            # the last url should be url_5, and the remaining urls
            # (url_0 through url_4) were not included in the first page
            ("Returns the first page of urls", 0, "url_29", "url_5"),
            ("Returns the second page of urls", 1, "url_4", "url_0"),
        ]
        for test_name, page, first_alias, last_alias in cases:
            with self.subTest(
                test_name=test_name, first_alias=first_alias, last_alias=last_alias
            ):
                with tempfile.NamedTemporaryFile() as tmp:
                    sqlite_helpers.maybe_create_table(tmp.name)
                    # create 30 urls with aliases url_0 to url_29
                    for i in range(30):
                        alias = f"url_{i}"
                        sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, alias)
                    stuff = sqlite_helpers.get_urls(tmp.name, page)
                    self.assertEqual(stuff[0]["alias"], first_alias)
                    self.assertEqual(stuff[-1]["alias"], last_alias)

    def test_get_urls_page_search(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            # create 30 urls with aliases url_0 to url_29
            for i in range(30):
                alias = f"url_{i}"
                sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, alias)
            # we should get a full page of answers with a vague search term
            stuff = sqlite_helpers.get_urls(tmp.name, search="url")
            self.assertEqual(len(stuff), sqlite_helpers.ROWS_PER_PAGE)
            # we should get one answer with a specfic search term
            stuff = sqlite_helpers.get_urls(tmp.name, search="url_0")
            self.assertEqual(len(stuff), 1)
            # we should get nothing with a not found search term
            stuff = sqlite_helpers.get_urls(tmp.name, search="not_real")
            self.assertEqual(len(stuff), 0)

    def test_get_url(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, "home")
            result = sqlite_helpers.get_url(tmp.name, "home")
            self.assertEqual(result, self.EXAMPLE_URL)
            # not found alias returns None
            result = sqlite_helpers.get_url(tmp.name, "not_real")
            self.assertIsNone(result, self.EXAMPLE_URL)

    def test_get_url_expired(self):
        # querying a url that has expired returns nothing
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            sqlite_helpers.insert_url(
                tmp.name, self.EXAMPLE_URL, "home", self.EXAMPLE_DATETIME.isoformat()
            )
            result = sqlite_helpers.get_url(tmp.name, "home")
            self.assertIsNone(result)

    def test_delete_url(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, "home")
            self.assertIsNotNone(sqlite_helpers.get_url(tmp.name, "home"))

            result = sqlite_helpers.delete_url(tmp.name, "home")
            self.assertTrue(result)
            self.assertIsNone(sqlite_helpers.get_url(tmp.name, "home"))

            # trying to delete the same url again returls false
            result_second_call = sqlite_helpers.get_url(tmp.name, "home")
            self.assertFalse(result_second_call)

    def test_get_number_of_entries(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            for i in range(30):
                alias = f"url_{i}"
                sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, alias)
            result = sqlite_helpers.get_number_of_entries(tmp.name)
            self.assertEqual(result, 30)
            result_with_search = sqlite_helpers.get_number_of_entries(tmp.name, "url_1")
            # matches url_1 and url_10 - url_19
            self.assertEqual(result_with_search, 11)
            result_with_search = sqlite_helpers.get_number_of_entries(
                tmp.name, "not_real"
            )
            self.assertEqual(result_with_search, 0)

    def test_increment_used_column(self):
        with tempfile.NamedTemporaryFile() as tmp:
            sqlite_helpers.maybe_create_table(tmp.name)
            sqlite_helpers.insert_url(tmp.name, self.EXAMPLE_URL, "home")
            db = sqlite3.connect(tmp.name)
            cursor = db.cursor()

            cursor.execute("SELECT used FROM urls;")
            [used] = cursor.fetchone()
            self.assertEqual(used, 1)

            sqlite_helpers.increment_used_column(tmp.name, "home")
            cursor.execute("SELECT used FROM urls;")
            [used] = cursor.fetchone()
            self.assertEqual(used, 2)

            sqlite_helpers.increment_used_column(tmp.name, "home", 20)
            cursor.execute("SELECT used FROM urls;")
            [used] = cursor.fetchone()
            self.assertEqual(used, 22)


if __name__ == "__main__":
    unittest.main()
