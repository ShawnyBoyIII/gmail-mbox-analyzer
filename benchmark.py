import time
import mailbox
import tempfile
from pathlib import Path
from email.message import EmailMessage
from src.gmail_storage_cleaner.analyzer import analyze_mbox, write_csv_reports, AnalysisResult, SenderRecord, AttachmentRecord

def build_message(sender: str, subject: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "me@example.com"
    message["Subject"] = subject
    message.set_content("hello")
    return message

def run_mbox_benchmark():
    with tempfile.TemporaryDirectory() as temp_dir:
        mbox_path = Path(temp_dir) / "large.mbox"
        mbox = mailbox.mbox(str(mbox_path))

        print("Generating test data for mbox benchmark...")
        senders = [f"Sender {i} <sender{i}@example.com>" for i in range(10)]
        messages_per_sender = 2000

        for i in range(messages_per_sender):
            for sender in senders:
                mbox.add(build_message(sender, f"Message {i}"))
        mbox.flush()
        mbox.close()

        print(f"Running analyze_mbox benchmark on {len(senders) * messages_per_sender} messages...")
        start_time = time.perf_counter()
        analyze_mbox(mbox_path)
        end_time = time.perf_counter()

        print(f"analyze_mbox execution time: {end_time - start_time:.4f} seconds")

def run_csv_benchmark():
    print("\nGenerating test data for CSV writer benchmark...")

    # Generate a large number of records
    num_records = 100000

    sender_records = [
        SenderRecord(
            sender_email=f"sender{i}@example.com",
            sender_name=f"Sender Name {i}",
            domain="example.com",
            count=100 + i,
            bulk_count=10,
            gmail_search=f"from:sender{i}@example.com"
        )
        for i in range(num_records)
    ]

    attachment_records = [
        AttachmentRecord(
            sender_email=f"sender{i}@example.com",
            sender_name=f"Sender Name {i}",
            subject=f"Subject {i}",
            date="2023-01-01 12:00:00",
            attachment_count=2,
            total_attachment_bytes=2048,
            total_attachment_mb=0.002,
            gmail_search=f"from:sender{i}@example.com has:attachment"
        )
        for i in range(num_records)
    ]

    result = AnalysisResult(
        total_messages=num_records * 10,
        sender_counts=sender_records,
        mid_volume_sender_counts=sender_records[:1000],
        domain_counts=[("example.com", num_records * 10)],
        bulk_sender_counts=sender_records[:5000],
        heaviest_attachment_emails=attachment_records,
        unknown_sender_count=0
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Running write_csv_reports benchmark with {num_records} sender and attachment records...")
        start_time = time.perf_counter()
        write_csv_reports(result, temp_dir)
        end_time = time.perf_counter()

        print(f"write_csv_reports execution time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    run_mbox_benchmark()
    run_csv_benchmark()
