import json
import re

def clean(input_file_path: str, output_file_path: str) -> None:
    def remove_html_tags_and_entities(text: str) -> str:
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Replace HTML entities with their corresponding character
        text = re.sub(r'&nbsp;', ' ', text)
        return text.strip()

    with open(input_file_path, 'r') as infile, open(output_file_path, 'w') as outfile:
        for line in infile:
            record = json.loads(line)
            for key, value in record.items():
                if isinstance(value, str):
                    record[key] = remove_html_tags_and_entities(value)
            outfile.write(json.dumps(record) + '\n')

clean("/Users/aadinashikkar/Desktop/agentops-hack/input_jsonl/html_example.jsonl", "/Users/aadinashikkar/Desktop/agentops-hack/input_jsonl/cleaned_output.jsonl")