from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .analyzer import AnalysisResult, analyze_mbox, write_csv_reports


def parse_date(date_string: str) -> datetime:
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_string}'. Use YYYY-MM-DD."
        )


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
    parser.add_argument(
        "--search",
        type=str,
        help="Filter results by matching this keyword against sender names or emails.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive review mode to build a bulk deletion search query.",
    )
    return parser


def do_interactive_mode(result: AnalysisResult) -> None:
    print("\n--- Interactive Bulk Deletion Review ---")
    print(
        "Reviewing top senders. Press 'y' to add to bulk delete query, 'n' to skip, 'q' to quit."
    )

    search_parts = []
    total_messages_to_delete = 0

    for r in result.sender_counts:
        display_name = f" ({r.sender_name})" if r.sender_name else ""
        prompt = f"Add {r.sender_email}{display_name} ({r.count} messages)? [y/N/q]: "

        try:
            choice = input(prompt).strip().lower()
        except EOFError:
            break

        if choice == "q":
            break
        elif choice == "y":
            search_parts.append(r.gmail_search)
            total_messages_to_delete += r.count

    if not search_parts:
        print("\nNo senders selected.")
        return

    print(f"\n--- Selected for Deletion: {total_messages_to_delete} messages ---")
    print("\nGmail Search Query (copy & paste to delete):")
    print(" OR ".join(search_parts))
    print("")


def render_search_summary(result: AnalysisResult, keyword: str) -> str:
    keyword = keyword.lower()
    matches = [
        r
        for r in result.sender_counts
        if keyword in r.sender_email.lower() or keyword in r.sender_name.lower()
    ]

    lines: list[str] = []
    if not matches:
        lines.append(f"No senders found matching '{keyword}'.")
        return "\n".join(lines)

    lines.append(f"Found {len(matches)} senders matching '{keyword}':")
    total_messages = 0
    search_parts = []

    for i, r in enumerate(matches, start=1):
        display_name = f" ({r.sender_name})" if r.sender_name else ""
        lines.append(f"  {i:>2}. {r.sender_email}{display_name} - {r.count} messages")
        total_messages += r.count
        search_parts.append(r.gmail_search)

    lines.append("")
    lines.append(f"Total messages across these senders: {total_messages}")
    lines.append("Gmail Search Query (copy & paste to delete):")
    lines.append(" OR ".join(search_parts))
    return "\n".join(lines)


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

    bulk_candidates = [
        record for record in result.sender_counts if record.bulk_count > 0
    ][: min(top, 10)]
    lines.append("")
    lines.append("Suggested Gmail searches for likely cleanup:")
    if not bulk_candidates:
        lines.append("  No likely bulk senders were detected in the current results.")
    else:
        for index, record in enumerate(bulk_candidates, start=1):
            lines.append(
                f"  {index:>2}. {record.gmail_search} ({record.bulk_count} likely bulk messages)"
            )

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

    if args.interactive:
        do_interactive_mode(result)
    elif args.search:
        print(render_search_summary(result, args.search))
    else:
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
