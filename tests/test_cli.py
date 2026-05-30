from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from src.gmail_mbox_analyzer.analyzer import AnalysisResult, SenderRecord
from src.gmail_mbox_analyzer.cli import render_search_summary, do_interactive_mode


class CliTests(unittest.TestCase):
    def setUp(self):
        self.result = AnalysisResult(
            total_messages=100,
            sender_counts=[
                SenderRecord(
                    sender_email="uber@example.com",
                    sender_name="Uber",
                    domain="example.com",
                    count=50,
                    bulk_count=0,
                    gmail_search="from:uber@example.com",
                ),
                SenderRecord(
                    sender_email="lyft@example.com",
                    sender_name="Lyft",
                    domain="example.com",
                    count=30,
                    bulk_count=0,
                    gmail_search="from:lyft@example.com",
                ),
                SenderRecord(
                    sender_email="uber.eats@example.com",
                    sender_name="",
                    domain="example.com",
                    count=20,
                    bulk_count=0,
                    gmail_search="from:uber.eats@example.com",
                ),
            ],
            mid_volume_sender_counts=[],
            domain_counts=[],
            bulk_sender_counts=[],
            heaviest_attachment_emails=[],
            unknown_sender_count=0,
        )

    def test_search_mode(self):
        output = render_search_summary(self.result, "uber")

        self.assertIn("Found 2 senders matching 'uber'", output)
        self.assertIn("Total messages across these senders: 70", output)
        self.assertIn("from:uber@example.com OR from:uber.eats@example.com", output)
        self.assertNotIn("lyft@example.com", output)

    def test_search_mode_no_matches(self):
        output = render_search_summary(self.result, "doordash")

        self.assertIn("No senders found matching 'doordash'", output)

    @patch("builtins.input", side_effect=["y", "n", "y"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_interactive_mode(self, mock_stdout, mock_input):
        do_interactive_mode(self.result)
        output = mock_stdout.getvalue()

        self.assertIn("Selected for Deletion: 70 messages", output)
        self.assertIn("from:uber@example.com OR from:uber.eats@example.com", output)
        self.assertNotIn("lyft", output.split("OR"))  # Lyft was 'n'

    @patch("builtins.input", side_effect=["n", "q"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_interactive_mode_quit(self, mock_stdout, mock_input):
        do_interactive_mode(self.result)
        output = mock_stdout.getvalue()

        self.assertIn("No senders selected.", output)

    def test_parse_date_valid(self):
        from src.gmail_mbox_analyzer.cli import parse_date
        from datetime import datetime

        dt = parse_date("2023-01-01")
        self.assertEqual(dt, datetime(2023, 1, 1))

    def test_parse_date_invalid(self):
        from src.gmail_mbox_analyzer.cli import parse_date
        import argparse

        with self.assertRaises(argparse.ArgumentTypeError):
            parse_date("01-01-2023")

    def test_build_parser_defaults(self):
        from src.gmail_mbox_analyzer.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["my_inbox.mbox"])

        self.assertEqual(args.mbox_path, "my_inbox.mbox")
        self.assertEqual(args.top, 20)
        self.assertFalse(args.bulk_only)
        self.assertEqual(args.exclude_domain, [])
        self.assertIsNone(args.output_dir)
        self.assertIsNone(args.start_date)
        self.assertIsNone(args.end_date)
        self.assertIsNone(args.search)
        self.assertFalse(args.interactive)

    def test_build_parser_all_args(self):
        from src.gmail_mbox_analyzer.cli import build_parser
        from datetime import datetime

        parser = build_parser()
        args = parser.parse_args(
            [
                "my_inbox.mbox",
                "--top",
                "50",
                "--bulk-only",
                "--exclude-domain",
                "example.com",
                "--exclude-domain",
                "test.com",
                "--output-dir",
                "/tmp/output",  # nosec B108
                "--start-date",
                "2023-01-01",
                "--end-date",
                "2023-12-31",
                "--search",
                "uber",
                "--interactive",
            ]
        )

        self.assertEqual(args.mbox_path, "my_inbox.mbox")
        self.assertEqual(args.top, 50)
        self.assertTrue(args.bulk_only)
        self.assertEqual(args.exclude_domain, ["example.com", "test.com"])
        self.assertEqual(args.output_dir, "/tmp/output")  # nosec B108
        self.assertEqual(args.start_date, datetime(2023, 1, 1))
        self.assertEqual(args.end_date, datetime(2023, 12, 31))
        self.assertEqual(args.search, "uber")
        self.assertTrue(args.interactive)
