## based

```bash
source venv/bin/activate
basedpyright
```

## ruff

```bash
source venv/bin/activate
ruff check src/ tests/ --output-format=concise
ruff format --check src/ tests/
```

## bandit

```bash
source venv/bin/activate
bandit -r src scripts \
  --exclude ".svn,CVS,.bzr,.hg,.git,__pycache__,.tox,.eggs,*.egg,venv,dist,build,scripts/copy_addon_to_addons21.py" \
  --severity-level low \
  --confidence-level low \
  --format txt \
  -v
```

## test

```bash
source venv/bin/activate
QT_QPA_PLATFORM=offscreen pytest tests/ -v --tb=short --without-integration --cov=src --cov-report=xml
```

## ci

```bash
mask based
mask ruff
mask bandit
mask test
```


