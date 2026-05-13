from __future__ import annotations

import mailbox
import tempfile
import unittest
from email.header import Header
from email.message import EmailMessage
from pathlib import Path

from src.gmail_mbox_analyzer.analyzer import analyze_mbox, write_csv_reports


def build_message(sender: str, subject: str, **headers: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "me@example.com"
    message["Subject"] = subject
    for key, value in headers.items():
        message[key] = value
    message.set_content("hello")
    return message


def build_message_with_attachment(sender: str, subject: str, attachment_bytes: bytes) -> EmailMessage:
    message = build_message(sender, subject)
    message.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="octet-stream",
        filename="file.bin",
    )
    return message


class AnalyzerTests(unittest.TestCase):
    def create_mbox(self, messages: list[EmailMessage]) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        mbox_path = Path(temp_dir.name) / "sample.mbox"
        mbox = mailbox.mbox(str(mbox_path))
        for message in messages:
            mbox.add(message)
        mbox.flush()
        mbox.close()
        return mbox_path

    def test_counts_senders_and_bulk_headers(self) -> None:
        mbox_path = self.create_mbox(
            [
                build_message("News <news@example.com>", "A", **{"List-Unsubscribe": "<mailto:bye@example.com>"}),
                build_message("News <news@example.com>", "B"),
                build_message("Store <sales@shop.com>", "C", Precedence="bulk"),
                build_message("Friend <pal@gmail.com>", "D"),
            ]
        )

        result = analyze_mbox(mbox_path)

        self.assertEqual(result.total_messages, 4)
        self.assertEqual(result.unknown_sender_count, 0)
        self.assertEqual(result.sender_counts[0].sender_email, "news@example.com")
        self.assertEqual(result.sender_counts[0].count, 2)
        self.assertEqual(result.sender_counts[0].bulk_count, 1)
        self.assertEqual(result.sender_counts[0].gmail_search, "from:news@example.com")
        self.assertEqual(result.sender_counts[1].sender_email, "pal@gmail.com")
        self.assertEqual(result.domain_counts[0], ("example.com", 2))
        self.assertEqual(result.domain_counts[1], ("gmail.com", 1))
        self.assertEqual(result.domain_counts[2], ("shop.com", 1))

    def test_bulk_only_filters_non_bulk_messages(self) -> None:
        mbox_path = self.create_mbox(
            [
                build_message("News <news@example.com>", "A", **{"List-Id": "list.example.com"}),
                build_message("Friend <pal@gmail.com>", "B"),
            ]
        )

        result = analyze_mbox(mbox_path, bulk_only=True)

        self.assertEqual(len(result.sender_counts), 1)
        self.assertEqual(result.sender_counts[0].sender_email, "news@example.com")

    def test_exclude_domains(self) -> None:
        mbox_path = self.create_mbox(
            [
                build_message("News <news@example.com>", "A"),
                build_message("Friend <pal@gmail.com>", "B"),
            ]
        )

        result = analyze_mbox(mbox_path, exclude_domains={"gmail.com"})

        self.assertEqual(len(result.sender_counts), 1)
        self.assertEqual(result.sender_counts[0].sender_email, "news@example.com")

    def test_writes_csv_outputs(self) -> None:
        mbox_path = self.create_mbox([build_message("News <news@example.com>", "A")])
        result = analyze_mbox(mbox_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_paths = write_csv_reports(result, temp_dir)
            self.assertEqual(len(output_paths), 5)
            for path in output_paths:
                self.assertTrue(path.exists())

    def test_header_object_sender_is_supported(self) -> None:
        message = EmailMessage()
        message["From"] = Header("Sender Name <sender@example.com>")
        message["To"] = "me@example.com"
        message["Subject"] = "Header object"
        message.set_content("hello")

        mbox_path = self.create_mbox([message])
        result = analyze_mbox(mbox_path)

        self.assertEqual(result.sender_counts[0].sender_email, "sender@example.com")

    def test_mid_volume_senders_and_heavy_attachments(self) -> None:
        messages = [
            build_message("Big Sender <big@example.com>", f"Message {index}")
            for index in range(150)
        ]
        messages.extend(
            [
                build_message_with_attachment("Attach <attach@example.com>", "Small attachment", b"a" * 512),
                build_message_with_attachment("Attach <attach@example.com>", "Large attachment", b"a" * 4096),
                build_message_with_attachment("Other <other@example.com>", "Medium attachment", b"a" * 2048),
            ]
        )

        mbox_path = self.create_mbox(messages)
        result = analyze_mbox(mbox_path)

        self.assertEqual(len(result.mid_volume_sender_counts), 1)
        self.assertEqual(result.mid_volume_sender_counts[0].sender_email, "big@example.com")
        self.assertEqual(result.mid_volume_sender_counts[0].count, 150)
        self.assertEqual(result.heaviest_attachment_emails[0].subject, "Large attachment")
        self.assertEqual(result.heaviest_attachment_emails[0].sender_email, "attach@example.com")


if __name__ == "__main__":
    unittest.main()
