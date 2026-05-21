from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from src.gmail_mbox_analyzer.analyzer import AnalysisResult, SenderRecord
from src.gmail_mbox_analyzer.cli import do_search_summary, do_interactive_mode


class CliTests(unittest.TestCase):
    def setUp(self):
        self.result = AnalysisResult(
            total_messages=100,
            sender_counts=[
                SenderRecord(sender_email="uber@example.com", sender_name="Uber", domain="example.com", count=50, bulk_count=0, gmail_search="from:uber@example.com"),
                SenderRecord(sender_email="lyft@example.com", sender_name="Lyft", domain="example.com", count=30, bulk_count=0, gmail_search="from:lyft@example.com"),
                SenderRecord(sender_email="uber.eats@example.com", sender_name="", domain="example.com", count=20, bulk_count=0, gmail_search="from:uber.eats@example.com"),
            ],
            mid_volume_sender_counts=[],
            domain_counts=[],
            bulk_sender_counts=[],
            heaviest_attachment_emails=[],
            unknown_sender_count=0
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_search_mode(self, mock_stdout):
        do_search_summary(self.result, "uber")
        output = mock_stdout.getvalue()

        self.assertIn("Found 2 senders matching 'uber'", output)
        self.assertIn("Total messages across these senders: 70", output)
        self.assertIn("from:uber@example.com OR from:uber.eats@example.com", output)
        self.assertNotIn("lyft@example.com", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_search_mode_no_matches(self, mock_stdout):
        do_search_summary(self.result, "doordash")
        output = mock_stdout.getvalue()

        self.assertIn("No senders found matching 'doordash'", output)

    @patch('builtins.input', side_effect=['y', 'n', 'y'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_interactive_mode(self, mock_stdout, mock_input):
        do_interactive_mode(self.result)
        output = mock_stdout.getvalue()

        self.assertIn("Selected for Deletion: 70 messages", output)
        self.assertIn("from:uber@example.com OR from:uber.eats@example.com", output)
        self.assertNotIn("lyft", output.split("OR"))  # Lyft was 'n'

    @patch('builtins.input', side_effect=['n', 'q'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_interactive_mode_quit(self, mock_stdout, mock_input):
        do_interactive_mode(self.result)
        output = mock_stdout.getvalue()

        self.assertIn("No senders selected.", output)

if __name__ == "__main__":
    unittest.main()
