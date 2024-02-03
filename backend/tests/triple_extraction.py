import re

def extract_content(text):
    pattern = r'\{([^}]+)\}|\(([^)]+)\)'
    matches = re.findall(pattern, text)
    return [match[0] or match[1] for match in matches]

# Example usage:
text = "This is some {text} with (brackets)."
content = extract_content(text)
print(content)
