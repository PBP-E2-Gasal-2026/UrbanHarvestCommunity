#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    python_bin="$PYTHON_BIN"
elif [[ -x "$project_root/.venv/bin/python" ]]; then
    python_bin="$project_root/.venv/bin/python"
else
    python_bin="python3"
fi

"$python_bin" manage.py shell <<'PY'
from authentication.models import ROLE_CHOICES, Role

for name, label in ROLE_CHOICES:
    _, created = Role.objects.get_or_create(
        name=name,
        defaults={'description': label},
    )
    status = 'dibuat' if created else 'sudah ada'
    print(f'{name}: {status}')
PY
