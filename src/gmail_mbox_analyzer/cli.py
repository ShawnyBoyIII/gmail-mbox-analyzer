from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .analyzer import AnalysisResult, analyze_mbox, write_csv_reports


def parse_date(date_string: str) -> datetime:
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_string}'. Use YYYY-MM-DD.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a Gmail MBOX export and summarize message senders."
    )
    parser.add_argument("mbox_path", help="Path to the .mbox file to analyze.")
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of rows to show in the terminal summary. Default: 20.",
    )
    parser.add_argument(
        "--bulk-only",
        action="store_true",
        help="Only count likely bulk or newsletter messages.",
    )
    parser.add_argument(
        "--exclude-domain",
        action="append",
        default=[],
        help="Exclude one or more sender domains. Can be repeated.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for CSV reports.",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Optional start date for filtering messages (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="Optional end date for filtering messages (YYYY-MM-DD).",
    )
    return parser


def render_summary(result: AnalysisResult, top: int) -> str:
    lines: list[str] = []
    lines.append(f"Total messages scanned: {result.total_messages}")
    lines.append(f"Messages without a parseable sender: {result.unknown_sender_count}")
    lines.append("")
    lines.append(f"Top {min(top, len(result.sender_counts))} senders:")

    if not result.sender_counts:
        lines.append("  No matching senders found.")
    else:
        for index, record in enumerate(result.sender_counts[:top], start=1):
            display_name = f" ({record.sender_name})" if record.sender_name else ""
            lines.append(
                f"  {index:>2}. {record.sender_email}{display_name} - "
                f"{record.count} messages, {record.bulk_count} likely bulk"
            )

    lines.append("")
    lines.append("Top sender domains:")
    if not result.domain_counts:
        lines.append("  No matching domains found.")
    else:
        for index, (domain, count) in enumerate(result.domain_counts[:top], start=1):
            domain_label = domain or "<unknown>"
            lines.append(f"  {index:>2}. {domain_label} - {count} messages")

    lines.append("")
    lines.append("Senders with more than 100 and less than 1000 emails:")
    if not result.mid_volume_sender_counts:
        lines.append("  No senders are in that range.")
    else:
        for index, record in enumerate(result.mid_volume_sender_counts[:top], start=1):
            display_name = f" ({record.sender_name})" if record.sender_name else ""
            lines.append(
                f"  {index:>2}. {record.sender_email}{display_name} - "
                f"{record.count} messages, search: {record.gmail_search}"
            )

    lines.append("")
    lines.append("Top 10 emails with the heaviest attachments:")
    if not result.heaviest_attachment_emails:
        lines.append("  No attachment-heavy emails were detected.")
    else:
        for index, record in enumerate(result.heaviest_attachment_emails, start=1):
            display_name = f" ({record.sender_name})" if record.sender_name else ""
            subject = record.subject or "<no subject>"
            lines.append(
                f"  {index:>2}. {record.sender_email}{display_name} - "
                f"{record.total_attachment_mb:.2f} MB across {record.attachment_count} attachment(s) - "
                f"{subject}"
            )

    bulk_candidates = [record for record in result.sender_counts if record.bulk_count > 0][: min(top, 10)]
    lines.append("")
    lines.append("Suggested Gmail searches for likely cleanup:")
    if not bulk_candidates:
        lines.append("  No likely bulk senders were detected in the current results.")
    else:
        for index, record in enumerate(bulk_candidates, start=1):
            lines.append(f"  {index:>2}. {record.gmail_search} ({record.bulk_count} likely bulk messages)")

    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    mbox_path = Path(args.mbox_path)
    if not mbox_path.exists():
        parser.error(f"MBOX file not found: {mbox_path}")

    result = analyze_mbox(
        mbox_path,
        exclude_domains=set(args.exclude_domain),
        bulk_only=args.bulk_only,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(render_summary(result, args.top))

    if args.output_dir:
        output_paths = write_csv_reports(result, args.output_dir)
        print("")
        print("CSV reports written:")
        for path in output_paths:
            print(f"  - {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
