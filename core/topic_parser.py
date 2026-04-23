import json
import re

def parse_text_to_json(input_file, output_file="topics.json"):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    topics = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        match = re.match(r"(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.+)", line)

        if match:
            timestamp = match.group(1)
            title = match.group(2)

            message = ""
            if i + 1 < len(lines):
                message = lines[i + 1].strip()

            topics.append({
                "at": timestamp,
                "title": title,
                "message": message
            })

            i += 2
        else:
            i += 1

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

    print("topics.json generated successfully")

    return topics