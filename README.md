# moneno

## Prerequisites
- `uv` installed
- `uv tool update-shell` run once (puts `~/.local/bin` on PATH for bash/fish/zsh), then restart the shell
- WSL: clone into the Linux filesystem (`~/`), not `/mnt/c/...`

## Quickstart
```bash
git clone <repo-url>
cd moneno
make setup
moneno-x --install-completion   # optional: tab-complete experiment names
```
Changes in `src/` take effect immediately (editable install). After pulling a new official tool, re-run `make setup`.

## Tools
| Command | Purpose | Example |
|---|---|---|
| `pdf-merge` | Merge PDFs | `pdf-merge a.pdf b.pdf -o out.pdf` |
| `docx-images` | Extract original-quality images from a .docx | `docx-images report.docx -o imgs/` |
| `moneno-x` | Run any experimental script | `moneno-x sample_experiment` |

## Experiment
```bash
moneno-x --new my_idea      # creates src/moneno/experimental/my_idea.py
moneno-x my_idea            # run it
moneno-x                    # list all experiments
```
- Rules: one self-contained file; unique name (prefix your handle if unsure); don't import other experiments.
- Need a package? `uv add --optional experimental <pkg>`, then `make setup`. Commit `pyproject.toml` and `uv.lock`. If it won't resolve, don't push.
- Push freely. Nothing here is listed in `[project.scripts]` or installed as its own command.

## Promote to the team CLI
1. Move logic from `experimental/` into `src/moneno/<tool>.py` with a Typer `app`.
2. Add one line under `[project.scripts]` in `pyproject.toml`.
3. Run `make setup`.

## Develop and test
```bash
make test
```

## Uninstall
`make uninstall`
