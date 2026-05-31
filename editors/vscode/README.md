# Glossolalia for VS Code

Syntax highlighting for the [Glossolalia](https://github.com/noisyloop/glossolalia)
language — *utterance is execution*.

Highlights `.glo` scrolls: commands (`speak`, `burn`, …), block keywords
(`incant`, `voice`, `ritual`, …), word-operators (`scale by`, `above`,
`weave`, …), types, `~` comments, glyphs, and `pulse`/`tone` numbers.

## Install (from source)

This extension is not yet on the Marketplace. To use it locally:

```bash
# copy (or symlink) this folder into your VS Code extensions directory
cp -r editors/vscode ~/.vscode/extensions/glossolalia-0.1.0
```

Then reload VS Code. Open any `.glo` file and it will light up.

To package it as a `.vsix` instead:

```bash
npm install -g @vscode/vsce
cd editors/vscode
vsce package
```

## What it knows

| Scope | Words |
|-------|-------|
| commands | `speak hush burn rise fall drift silence open close send sync chant remember forget` |
| blocks | `incant voice ritual invoke call takes end` |
| control | `if else repeat until in echo breathe` |
| operators | `is not above below and or` · `add subtract scale modulate ascend descend` · `weave unweave count at fracture converge` |
| types | `tone pulse glyph flicker sigil` |
| structure | `let be set to by with for as` |

See [SPEC.md](../../SPEC.md) for the full language.
