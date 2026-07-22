import os
import re

TEST_DIR = 'tests'

async_methods = [
    'create_session', 'get_sessions', 'get_session_history', 
    'save_session_message', 'update_session_title', 'delete_session', 
    'get_session_prompt', 'update_session_prompt', 'process_message'
]

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Add pytest.mark.asyncio to test functions
    # Matches `def test_xyz(`
    content = re.sub(r'^(    )?def test_([a-zA-Z0-9_]+)\(', 
                     r'\1@pytest.mark.asyncio\n\1async def test_\2(', 
                     content, flags=re.MULTILINE)

    # 2. Add await before the async methods
    for method in async_methods:
        # We want to replace `method(` with `await method(` if it's not already awaited
        pattern = r'(?<!def )(?<!await )(?<!async def )(?<!import )(?<!\.)\b' + method + r'\s*\('
        content = re.sub(pattern, f'await {method}(', content)

        # Also handle `app.storage.method(` or `agy_client.method(`
        pattern2 = r'(?<!await )([a-zA-Z0-9_]+\.)' + method + r'\s*\('
        content = re.sub(pattern2, r'await \1' + method + '(', content)

    if '@pytest.mark.asyncio' in content and 'import pytest' not in content:
        content = 'import pytest\n' + content

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")

for f in ['test_storage.py', 'test_main.py', 'test_agy_client.py']:
    fix_file(os.path.join(TEST_DIR, f))
