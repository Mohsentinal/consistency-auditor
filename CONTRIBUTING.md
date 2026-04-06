# Contributing

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Quality checks

```bash
ruff check .
pytest -q
python -m build
```

## Release checklist

1. Update `CHANGELOG.md`
2. Bump `src/consistency_auditor/__init__.py` and `pyproject.toml`
3. Run lint, tests, and build
4. Merge to `main`
5. Create tag `vX.Y.Z`
6. Publish GitHub Release
7. Upload to PyPI with:

```bash
python -m twine upload dist/*
```
