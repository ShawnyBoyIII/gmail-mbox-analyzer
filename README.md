# Gmail MBOX Analyzer

Find the senders taking up the most space in your Gmail export so you can clean up your inbox faster.

This CLI analyzes a Gmail `.mbox` export and surfaces:

- top senders by message count
- likely bulk and newsletter mail
- senders with 100 to 1000 emails
- attachment-heavy messages worth reviewing first

**Personal result:** this workflow helped me delete more than 20,000 emails.

Gmail makes it surprisingly hard to understand who is sending you the most email at scale. You can search by sender, but Gmail does not give you an easy way to see sender counts across your whole mailbox, which makes bulk cleanup slow and frustrating.

This project was built to solve that problem. The tradeoff is that you first need to request and download an `.mbox` export from Gmail through Google Takeout, which is a little painful. Once you have the file, the analysis runs quickly and gives you a much clearer picture of where your inbox volume is coming from.

## Why I Built This

I wanted a practical way to answer a simple question that Gmail does not answer well: who is sending me the most email?

Once you know that, inbox cleanup becomes much more manageable. Instead of guessing, you can focus on:

- the senders creating the most volume
- likely newsletter and bulk-mail sources
- attachment-heavy messages that may be worth deleting first

## Sample Output

```text
Total messages scanned: 48,231
Messages without a parseable sender: 14

Top 5 senders:
   1. deals@example.com - 2,184 messages, 2,102 likely bulk
   2. notifications@service.com - 1,426 messages, 1,401 likely bulk
   3. updates@shopping.com - 988 messages, 964 likely bulk
   4. team@company.com - 312 messages, 0 likely bulk
   5. friend@gmail.com - 205 messages, 0 likely bulk

Senders with more than 100 and less than 1000 emails:
   1. updates@shopping.com - 988 messages, search: from:updates@shopping.com
   2. team@company.com - 312 messages, search: from:team@company.com
   3. friend@gmail.com - 205 messages, search: from:friend@gmail.com

Top 10 emails with the heaviest attachments:
   1. reports@vendor.com - 24.40 MB across 2 attachment(s) - Quarterly report
   2. photos@family.com - 18.12 MB across 7 attachment(s) - Vacation pictures
```

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
- Generates a Gmail filter import XML file to automatically Trash or Archive bulk senders

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

Generate a Gmail filter XML file to automatically Trash or Archive the top bulk senders. You can import this file into Gmail's settings:

```bash
python3 -m src.gmail_mbox_analyzer.cli /path/to/mail.mbox --export-filters ./mailFilters.xml --filter-action trash
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
- Add interactive review mode for likely newsletters and promotions
