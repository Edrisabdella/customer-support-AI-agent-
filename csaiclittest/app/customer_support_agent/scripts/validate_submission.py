from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]
PY_FILES = [ROOT/'agent/main.py', ROOT/'lambda/order_tracker.py', ROOT/'lambda/refund_processor.py']
required = [
    'BedrockAgentCoreApp', '@app.entrypoint', 'app.run()', 'MCPClient',
    'search_knowledge_base', 'retrieve(', 'MemoryHook', 'create_event',
    'calculate_loyalty_discount', 'code_session', 'AgentCoreBrowser'
]
for path in PY_FILES:
    ast.parse(path.read_text(encoding='utf-8'))
    print(f'OK syntax: {path.relative_to(ROOT)}')
text = (ROOT/'agent/main.py').read_text(encoding='utf-8')
for marker in required:
    if marker not in text:
        raise SystemExit(f'MISSING: {marker}')
if 'api_key' in text.lower() or 'password' in text.lower():
    raise SystemExit('Potential secret marker found in main.py')
json.load(open(ROOT/'lambda/lambda_schema.json', encoding='utf-8'))
print('OK rubric markers')
print('OK schema JSON')
print('Validation passed. AWS runtime tests still require the real deployed account.')
