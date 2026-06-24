import os
import glob

dirs_to_check = [
    '/home/dinh/Downloads/tf4-aio-03/docs/*.md',
    '/home/dinh/Downloads/tf4-aio-03/contracts/*.md'
]

files = []
for d in dirs_to_check:
    files.extend(glob.glob(d))

replacements = {
    '<Nhóm AI leader name>': 'AIO-03 Lead',
    '<Nhóm AI - Đề tài>': 'AIO-03 - Foresight Lens',
    '<Nhóm AI>': 'AIO-03',
    '<Đề tài>': 'Foresight Lens',
    'Task force <N>': 'Task force 4',
    'Nhóm AI <N>': 'AIO-03'
}

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

print("Done")
