import os
import sys
import glob

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package is required. Install it using 'pip install openai'.")
    sys.exit(1)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY environment variable not set. Exiting.")
        sys.exit(
            0
        )  # We exit gracefully so the CI doesn't fail if key is missing during some test runs

    client = OpenAI(api_key=api_key)

    # Find all python files in src/ and tests/
    files_to_scan = []
    for directory in ["src/**/*.py", "tests/**/*.py"]:
        files_to_scan.extend(glob.glob(directory, recursive=True))

    if not files_to_scan:
        print("No Python files found to scan.")
        sys.exit(0)

    print(f"Starting security scan on {len(files_to_scan)} files...")

    vulnerabilities_found = False

    for filepath in files_to_scan:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Skip empty files
            if not content.strip():
                continue

            prompt = (
                f"Review the following Python code for security vulnerabilities. "
                f"File: {filepath}\n\n"
                f"Code:\n```python\n{content}\n```\n\n"
                f"If you find any security vulnerabilities, explain them clearly and suggest a fix. "
                f"If there are no security vulnerabilities, just say 'No security vulnerabilities found.'"
            )

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert security engineer reviewing Python code.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = response.choices[0].message.content.strip()

            print(f"--- Analysis for {filepath} ---")
            print(result)
            print("-" * 40)

            if "No security vulnerabilities found" not in result:
                vulnerabilities_found = True

        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # If we want the action to fail on vulnerabilities, we can uncomment the below:
    if vulnerabilities_found:
        print("Vulnerabilities found. Review logs.")


if __name__ == "__main__":
    main()
