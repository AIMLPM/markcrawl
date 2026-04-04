# Contributing

Thanks for your interest in improving this project.

## How to contribute

1. Fork the repository.
2. Create a branch with a clear name.
3. Make focused changes.
4. Test your changes locally.
5. Open a pull request with a clear summary.

## Contribution guidelines

- Keep changes small and easy to review.
- Prefer improving readability over adding complexity.
- Preserve the crawler's core design goal: simple, dependable extraction for AI and indexing workflows.
- Add or update documentation when behavior changes.
- Avoid breaking the CLI without documenting it clearly.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Suggested checks before opening a PR

- Run the crawler against a small public test site.
- Confirm the generated files still include page content and `pages.jsonl`.
- Verify both `markdown` and `text` output modes.
- Verify `--show-progress` works as expected.

## Areas where help is especially useful

- tests
- CI setup
- duplicate-content detection
- canonical URL handling
- browser-rendered page support
- documentation and examples

## Pull request checklist

- [ ] I tested my changes locally
- [ ] I updated relevant docs
- [ ] I kept the change focused and reviewable
- [ ] I avoided unrelated refactors
