import time
import mailbox
import tempfile
from pathlib import Path
from email.message import EmailMessage
from src.gmail_mbox_analyzer.analyzer import analyze_mbox

def build_message(sender: str, subject: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "me@example.com"
    message["Subject"] = subject
    message.set_content("hello")
    return message

def run_benchmark():
    with tempfile.TemporaryDirectory() as temp_dir:
        mbox_path = Path(temp_dir) / "large.mbox"
        mbox = mailbox.mbox(str(mbox_path))

        print("Generating test data...")
        senders = [f"Sender {i} <sender{i}@example.com>" for i in range(10)]
        messages_per_sender = 2000

        for i in range(messages_per_sender):
            for sender in senders:
                mbox.add(build_message(sender, f"Message {i}"))
        mbox.flush()
        mbox.close()

        print(f"Running benchmark on {len(senders) * messages_per_sender} messages...")
        start_time = time.perf_counter()
        analyze_mbox(mbox_path)
        end_time = time.perf_counter()

        print(f"Execution time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()
