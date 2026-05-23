from __future__ import annotations

import csv
import mailbox
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path


@dataclass(frozen=True)
class SenderRecord:
    sender_email: str
    sender_name: str
    domain: str
    count: int
    bulk_count: int
    gmail_search: str


@dataclass(frozen=True)
class AttachmentRecord:
    sender_email: str
    sender_name: str
    subject: str
    date: str
    attachment_count: int
    total_attachment_bytes: int
    total_attachment_mb: float
    gmail_search: str


@dataclass(frozen=True)
class AnalysisResult:
    total_messages: int
    sender_counts: list[SenderRecord]
    mid_volume_sender_counts: list[SenderRecord]
    domain_counts: list[tuple[str, int]]
    bulk_sender_counts: list[SenderRecord]
    heaviest_attachment_emails: list[AttachmentRecord]
    unknown_sender_count: int


def normalize_sender(message: Message) -> tuple[str, str]:
    raw_from = header_to_text(message.get("From", ""))
    sender_name, sender_email = parseaddr(raw_from)
    normalized_email = sender_email.strip().lower()
    normalized_name = " ".join(sender_name.split())
    return normalized_email, normalized_name


def header_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()

    try:
        return str(make_header(decode_header(str(value)))).strip()
    except Exception:
        return str(value).strip()


def extract_domain(email_address: str) -> str:
    if "@" not in email_address:
        return ""
    return email_address.rsplit("@", 1)[1]


def is_likely_bulk(message: Message) -> bool:
    if message.get("List-Unsubscribe"):
        return True
    if message.get("List-Id"):
        return True

    precedence = message.get("Precedence", "").strip().lower()
    if precedence in {"bulk", "list", "junk"}:
        return True

    auto_submitted = message.get("Auto-Submitted", "").strip().lower()
    if auto_submitted and auto_submitted != "no":
        return True

    return False


def analyze_mbox(
    mbox_path: str | Path,
    *,
    exclude_domains: set[str] | None = None,
    bulk_only: bool = False,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> AnalysisResult:
    exclude_domains = {domain.lower() for domain in (exclude_domains or set())}
    sender_counter: Counter[str] = Counter()
    sender_name_map: dict[str, str] = {}
    sender_bulk_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    heaviest_attachment_emails: list[AttachmentRecord] = []
    total_messages = 0
    unknown_sender_count = 0

    # Make sure start_date and end_date are aware
    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    mbox = mailbox.mbox(str(mbox_path))
    try:
        for message in mbox:
            if start_date or end_date:
                date_header = message.get("Date")
                if not date_header:
                    continue
                try:
                    msg_date = parsedate_to_datetime(date_header)
                    if start_date and msg_date < start_date:
                        continue
                    if end_date and msg_date > end_date:
                        continue
                except (TypeError, ValueError):
                    continue

            total_messages += 1
            sender_email, sender_name = normalize_sender(message)
            if not sender_email:
                unknown_sender_count += 1
                continue

            domain = extract_domain(sender_email)
            if domain in exclude_domains:
                continue

            bulk = is_likely_bulk(message)
            if bulk_only and not bulk:
                continue

            sender_counter[sender_email] += 1
            if sender_email not in sender_name_map:
                sender_name_map[sender_email] = sender_name
            domain_counter[domain] += 1
            if bulk:
                sender_bulk_counter[sender_email] += 1

            attachment_record = build_attachment_record(message, sender_email, sender_name)
            if attachment_record is not None:
                heaviest_attachment_emails.append(attachment_record)
    finally:
        mbox.close()

    sender_records = build_sender_records(sender_counter, sender_name_map, sender_bulk_counter)
    mid_volume_sender_records = [record for record in sender_records if 100 < record.count < 1000]
    bulk_sender_records = [record for record in sender_records if record.bulk_count > 0]
    domain_counts = sorted(domain_counter.items(), key=lambda item: (-item[1], item[0]))
    heaviest_attachment_emails.sort(
        key=lambda record: (-record.total_attachment_bytes, -record.attachment_count, record.sender_email, record.subject)
    )

    return AnalysisResult(
        total_messages=total_messages,
        sender_counts=sender_records,
        mid_volume_sender_counts=mid_volume_sender_records,
        domain_counts=domain_counts,
        bulk_sender_counts=bulk_sender_records,
        heaviest_attachment_emails=heaviest_attachment_emails[:10],
        unknown_sender_count=unknown_sender_count,
    )


def build_sender_records(
    sender_counter: Counter[str],
    sender_name_map: dict[str, str],
    sender_bulk_counter: Counter[str],
) -> list[SenderRecord]:
    records: list[SenderRecord] = []
    for sender_email, count in sender_counter.items():
        records.append(
            SenderRecord(
                sender_email=sender_email,
                sender_name=sender_name_map.get(sender_email, ""),
                domain=extract_domain(sender_email),
                count=count,
                bulk_count=sender_bulk_counter.get(sender_email, 0),
                gmail_search=build_gmail_search(sender_email),
            )
        )
    return sorted(records, key=lambda record: (-record.count, record.sender_email))


def build_gmail_search(sender_email: str) -> str:
    return f"from:{sender_email}"


def build_message_gmail_search(sender_email: str, subject: str) -> str:
    if subject:
        escaped_subject = subject.replace('"', '\\"')
        return f'from:{sender_email} subject:"{escaped_subject}" has:attachment'
    return f"from:{sender_email} has:attachment"


def build_attachment_record(
    message: Message,
    sender_email: str,
    sender_name: str,
) -> AttachmentRecord | None:
    attachment_count = 0
    total_attachment_bytes = 0

    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = (part.get_content_disposition() or "").lower()
        filename = part.get_filename()
        if disposition != "attachment" and not filename:
            continue

        payload = part.get_payload(decode=True) or b""
        attachment_count += 1
        total_attachment_bytes += len(payload)

    if attachment_count == 0 or total_attachment_bytes == 0:
        return None

    subject = header_to_text(message.get("Subject", ""))
    date = header_to_text(message.get("Date", ""))
    return AttachmentRecord(
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        date=date,
        attachment_count=attachment_count,
        total_attachment_bytes=total_attachment_bytes,
        total_attachment_mb=round(total_attachment_bytes / (1024 * 1024), 2),
        gmail_search=build_message_gmail_search(sender_email, subject),
    )


def write_csv_reports(result: AnalysisResult, output_dir: str | Path) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sender_counts_path = output_path / "sender_counts.csv"
    domain_counts_path = output_path / "domain_counts.csv"
    bulk_sender_counts_path = output_path / "bulk_sender_counts.csv"
    mid_volume_sender_counts_path = output_path / "mid_volume_sender_counts.csv"
    heaviest_attachment_emails_path = output_path / "heaviest_attachment_emails.csv"

    with sender_counts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sender_email", "sender_name", "domain", "count", "bulk_count", "gmail_search"])
        for record in result.sender_counts:
            writer.writerow(
                [
                    record.sender_email,
                    record.sender_name,
                    record.domain,
                    record.count,
                    record.bulk_count,
                    record.gmail_search,
                ]
            )

    with domain_counts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["domain", "count"])
        writer.writerows(result.domain_counts)

    with mid_volume_sender_counts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sender_email", "sender_name", "domain", "count", "bulk_count", "gmail_search"])
        for record in result.mid_volume_sender_counts:
            writer.writerow(
                [
                    record.sender_email,
                    record.sender_name,
                    record.domain,
                    record.count,
                    record.bulk_count,
                    record.gmail_search,
                ]
            )

    with bulk_sender_counts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sender_email", "sender_name", "domain", "count", "bulk_count", "gmail_search"])
        for record in result.bulk_sender_counts:
            writer.writerow(
                [
                    record.sender_email,
                    record.sender_name,
                    record.domain,
                    record.count,
                    record.bulk_count,
                    record.gmail_search,
                ]
            )

    with heaviest_attachment_emails_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sender_email",
                "sender_name",
                "subject",
                "date",
                "attachment_count",
                "total_attachment_bytes",
                "total_attachment_mb",
                "gmail_search",
            ]
        )
        for record in result.heaviest_attachment_emails:
            writer.writerow(
                [
                    record.sender_email,
                    record.sender_name,
                    record.subject,
                    record.date,
                    record.attachment_count,
                    record.total_attachment_bytes,
                    record.total_attachment_mb,
                    record.gmail_search,
                ]
            )

    return [
        sender_counts_path,
        domain_counts_path,
        mid_volume_sender_counts_path,
        bulk_sender_counts_path,
        heaviest_attachment_emails_path,
    ]
