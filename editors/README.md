# Editor support

Syntax highlighting for Glossolalia scrolls (`.glo`).

- **[vscode/](vscode/)** — VS Code extension (TextMate grammar). Copy the
  folder into `~/.vscode/extensions/` or package it with `vsce`. See
  [vscode/README.md](vscode/README.md).
- **[vim/](vim/)** — Vim / Neovim syntax + filetype detection. Install with
  your plugin manager pointed at this repo, or copy the files:

  ```bash
  cp editors/vim/ftdetect/glo.vim   ~/.vim/ftdetect/
  cp editors/vim/syntax/glo.vim     ~/.vim/syntax/
  ```

  For Neovim, use `~/.config/nvim/` instead of `~/.vim/`.

Both highlight the full keyword vocabulary in [SPEC.md](../SPEC.md). A test
(`tests/test_editor_grammar.py`) keeps the VS Code grammar in lockstep with the
interpreter's keyword set, so highlighting never drifts from the language.
