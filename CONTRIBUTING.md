# Contributing

Contributions are welcome. Bug reports, fixes, documentation improvements, and small focused
enhancements are all useful.

## Types of contributions

### Report bugs

Please open an issue at:

<https://github.com/dan-s-github/api-electricityinfo-nz/issues>

Include:

- your operating system and Python version
- any relevant local setup details
- clear steps to reproduce the problem

### Fix bugs and implement features

Look through the issue tracker for work that is ready to pick up. Small, focused changes are
preferred.

### Improve documentation

Documentation updates are always welcome, whether in the README, hosted docs, docstrings, or
examples.

## Getting started

1. Fork the repository and clone your fork.
2. Install dependencies:

   ```bash
   uv sync
   ```

3. Create a branch for your work:

   ```bash
   git checkout -b name-of-your-change
   ```

## Running checks

```bash
uv run pytest
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/
```

Linting can also be run with pre-commit:

```bash
uv run pre-commit run -a
```

To install the hooks locally:

```bash
uv run pre-commit install
```

## Integration tests

Integration tests use real API credentials from `tests/secrets.yaml`.

Create `tests/secrets.yaml` from `tests/secrets.yaml.example`:

```yaml
client_id: your_client_id
client_secret: your_client_secret
```

If `tests/secrets.yaml` is missing, the integration tests skip automatically.

## Building

```bash
uv build
```

## Documentation

Build the documentation site locally with:

```bash
uv run --group docs sphinx-build -b html docs docs/_build/html
```

Then open the generated site:

```bash
open docs/_build/html/index.html
```

For live-reloading local preview:

```bash
uv run --group docs sphinx-autobuild docs docs/_build/html
```

## Pull request guidelines

1. Include tests for feature work or bug fixes when appropriate.
2. Update documentation when public behavior changes.
3. Keep pull requests focused and easy to review.
4. Open a draft pull request early if you want feedback during development.

Commit messages should follow the
[Conventional Commits](https://www.conventionalcommits.org) format. This repository includes
`commitlint` and validates commit messages in CI.

## Release notes

- Keep the README focused on library usage.
- Keep development, testing, and release workflow documentation in `CONTRIBUTING.md`.
- Releases are expected to be automated through Semantic Release in GitHub Actions, with versions
  derived from commit history.
