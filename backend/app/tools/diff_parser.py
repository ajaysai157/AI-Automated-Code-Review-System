import re

def extract_file_path(diff: str) -> str | None:
    match = re.search(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)

    if match:
        return match.group(1)

    return None


def extract_file_paths(diff: str) -> list[str]:
    return re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)

def split_diff_by_file(diff: str) -> list[str]:
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)

    return [section for section in sections if section.strip()]


def find_changed_line(diff: str, keyword: str) -> int | None:
    lines = diff.splitlines()
    current_line = None

    for line in lines:
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)

            if match:
                current_line = int(match.group(1))

        elif current_line is not None:
            if line.startswith("+"):
                if keyword in line:
                    return current_line
                current_line += 1

            elif line.startswith("-"):
                continue

            else:
                current_line += 1

    return None



if __name__ == "__main__":
    diff = """diff --git a/app.py b/app.py
+++ b/app.py
@@ -10,5 +10,5 @@
 def process(data):
     result = safe_function(data)
     log("processing")
+    result = eval(data)
     return result
"""

    multi_file_diff = """diff --git a/auth.py b/auth.py
+++ b/auth.py
@@ -20,2 +20,2 @@
+print(password)

diff --git a/payment.py b/payment.py
+++ b/payment.py
@@ -30,2 +30,2 @@
+eval(data)
"""

    print(extract_file_paths(multi_file_diff))
    print(extract_file_path(diff))
    print(find_changed_line(diff, "eval("))

    sections = split_diff_by_file(multi_file_diff)

    for section in sections:
        print("-----")
        print(section)