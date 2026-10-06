"""Adapt existing synthetic fixtures to the stage-3 isolated runner."""
from pathlib import Path
import re
import subprocess

for name in ['business-access-isolated', 'hpp-setup-isolated']:
    source = Path('/qa/tests/' + name + '.py').read_text()
    source = re.sub(r'postgresql\+asyncpg://[a-z_]+:[a-z-]+-test-only@selaris-[a-z-]+qa-db/[a-z_]+',
        'postgresql+asyncpg://business_admin:business-test-only@selaris-business-qa-db/business_qa', source)
    source = re.sub(r'selaris-[a-z-]+qa-db', 'selaris-business-qa-db', source)
    source = re.sub(r'(?<=POSTGRES_APP_USER == )([\'"])[a-z_]+\1', "'business_app'", source)
    target = Path('/tmp/ai-' + name + '.py')
    target.write_text(source)
    result = subprocess.run(['python', str(target)])
    print('REGRESSION', name, result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
