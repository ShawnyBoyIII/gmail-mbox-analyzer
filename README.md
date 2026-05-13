# Gmail MBOX Analyzer

This project analyzes a Gmail `.mbox` export and summarizes who sends you the most mail.

The main goal is to help identify high-volume senders that are strong deletion candidates in Gmail.

## Safe Publishing

This repository is safe to publish only if you keep your personal mailbox data out of GitHub.

Do not upload:

- any `.mbox` export from Gmail
- generated `reports/` CSV files
- downloaded archive files from Google Takeout
- local `.env` or credentials files if you add them later

The included `.gitignore` is configured to block those files by default.

## What It Does

- Reads a local `.mbox` file
- Counts messages by sender email address
- Counts messages by sender domain
- Highlights senders with more than 100 but fewer than 1000 messages
- Flags likely bulk or newsletter mail using common headers
- Finds the top 10 emails with the heaviest attachments
- Exports CSV reports for spreadsheet review

## Project Layout

- `src/gmail_mbox_analyzer/analyzer.py`: mailbox parsing and aggregation
- `src/gmail_mbox_analyzer/cli.py`: command-line entry point
- `tests/test_analyzer.py`: regression tests

## Gmail Export Path

The easiest way to get a bulk Gmail mailbox in MBOX format is usually Google Takeout.

1. Go to Google Takeout.
2. Export only `Mail`.
3. Download and extract the archive.
4. Locate the `.mbox` file, often inside a folder named `Takeout/Mail`.

## Run It

From this project folder:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/All\ mail\ Including\ Spam\ and\ Trash.mbox
```

You can also write CSV outputs:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/mail.mbox --output-dir ./reports
```

## Useful Options

Show only likely bulk senders:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/mail.mbox --bulk-only
```

Show the top 50 senders:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/mail.mbox --top 50
```

Ignore one or more sender domains:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/mail.mbox --exclude-domain gmail.com --exclude-domain google.com
```

## CSV Outputs

When `--output-dir` is provided, the app writes:

- `sender_counts.csv`
- `domain_counts.csv`
- `mid_volume_sender_counts.csv`
- `bulk_sender_counts.csv`
- `heaviest_attachment_emails.csv`

## Next Step Ideas

- Add date-range filtering
- Add Gmail search suggestions for bulk delete actions
- Add interactive review mode for likely newsletters and promotions
