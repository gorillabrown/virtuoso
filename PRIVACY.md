# Privacy Policy

**Effective:** 24 September 2026

**Applies to:** the Virtuoso plugin for Claude Code and Codex, published at
https://github.com/gorillabrown/virtuoso

Virtuoso collects nothing. It has no servers, accounts, telemetry, analytics or tracking,
and it sends nothing to its author or to anyone else. Everything it keeps about your work
stays in your project, and in the repository you keep it in.

## What Virtuoso stores, and where

- **In your project.** Virtuoso creates and maintains files there:
  - the registry, `Virtuoso/workspace-layout.json`;
  - your roadmap, completion ledger, lessons, findings, close-out reports and review
    records, at the paths the registry declares;
  - agent memory, under `.claude/agent-memory/`.

  They are ordinary files. You decide whether to commit them, and your repository's
  host and visibility settings decide who can see them.
- **In your home folder.** `~/.virtuoso/installs.json` records where each installed
  version of the plugin lives and when it was recorded, and `~/.virtuoso/bin/` holds two
  small launcher scripts that read it. The record holds file paths, version numbers and
  timestamps, and nothing from your project.

Virtuoso stores nothing anywhere else.

## Network

In use, Virtuoso makes no network requests of its own. The check it runs when a session
starts reads your project locally and writes nothing to it.

Two things can reach the network, and you control both:

- **Git.** If your project's git policy allows pushing, a ceremony may push your commits
  to your repository's own remote, and nowhere else.
- **An external work register.** If you register an outside tracker, such as a monday.com
  board, as your work register, Virtuoso prepares each change and your AI host carries it
  out through the connector you installed. That exchange is between your host, the
  connector and the tracker, under their privacy policies.

One script in the plugin does use the network: `scripts/release.py`, the maintainer's
release tool, which publishes Virtuoso's own releases to Virtuoso's own repositories. It
does nothing unless you run it.

## Your AI host

Virtuoso runs inside an AI coding host, such as Claude Code or Codex. The host and its
model provider process your conversations and the files your agent reads, under their
own terms and privacy policies. Virtuoso does not change what they collect.

## Removing Virtuoso's data

1. Uninstall the plugin.
2. Delete `~/.virtuoso/`.
3. Delete any project files you no longer want.

Nothing else remains.

## Changes and contact

Any change to this policy is published in this file, and the repository keeps its
history. Questions go to https://github.com/gorillabrown/virtuoso/issues.
