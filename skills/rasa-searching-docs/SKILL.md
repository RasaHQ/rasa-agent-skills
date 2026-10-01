---
name: rasa-searching-docs
description: >
  Answers questions about Rasa Pro and CALM by reading the documentation bundled
  locally in `.rasa/` (page index `llms.txt`, full text `llms-full.txt`). Use for
  ANY question about how Rasa works — concepts, keys in `config.yml` /
  `endpoints.yml` / `domain.yml`, flow steps, patterns, slots, CLI commands,
  integrations, channels, deployment, "what does X do", "how do I Y", "is Z
  supported" — and whenever no other rasa-* skill covers the request. Also use
  before answering about Rasa from memory: recalled knowledge is often from NLU-based
  Rasa (intents, stories, rules) or predates current CALM features. Not for Mantle
  projects — use mantle-docs there.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.16.0"
  docs-url: https://rasa.com/docs
allowed-tools: >-
  Read Grep Glob
  Bash(awk:*) Bash(grep:*) Bash(sed:*) Bash(uniq:*) Bash(sort:*) Bash(ls:*)
---

# Rasa documentation lookup

`rasa tools init` bundles the full Rasa documentation into `.rasa/` at the project
root, as two files:

- **`.rasa/llms.txt` — the page index.** One line per page: title, link, and a
  one-line description.
- **`.rasa/llms-full.txt` — the full text** of every page, one after another.

**Always use the index first.** Find the page in `llms.txt`, then read only that
page — or one section of it — from `llms-full.txt`.

## Answer from the docs, not from memory

Rasa has changed a lot across releases. What you recall is often NLU-based Rasa
(intents, stories, rules, NLU pipelines) or an early version of CALM, and config
keys, defaults, and step types have moved since. Read the page first. Then state
the page path you used (e.g. `Source: /reference/primitives/flow-steps`) so the
user can check it. If you answer without reading a page, say so explicitly rather
than implying the answer came from the docs.

## Make sure these are the right docs

These docs cover Rasa Pro with CALM, plus Rasa Studio and the older NLU-based
system. If the project has `agent.yml` and `integrations.yml` instead of
`config.yml` and `domain.yml`, or has `.rasa/docs/mantle/`, it is a Mantle project —
use the mantle-docs skill instead.

Within these docs:

- **Mantle pages** (`/mantle/...`, if your copy has them) describe a different
  engine. Never use them to answer about a CALM project.
- **NLU-based pages** (intents, entities, stories, rules, NLU components,
  coexistence) apply only if the project uses NLU, e.g. it has `data/nlu.yml` or NLU
  components in `config.yml`. A CALM assistant uses flows and an LLM command
  generator instead.
- **Studio pages** (`/studio/...` for Studio 1.x, `/studio/2.x/...` for Studio 2.x)
  describe the no-code UI. For a project on disk, answer from the `/pro/...` and
  `/reference/...` pages, which describe the YAML and Python files.

## Check the version

The docs describe the latest Rasa Pro release; the project may run an older one.
Find its version with `rasa --version`, or from the `rasa-pro` pin in
`pyproject.toml` or `requirements*.txt`.

Pages gate features with notes such as "New in 3.14", "Rasa Pro 3.16+", "available
starting from Rasa 3.14.0", or "3.11 and above". If a feature is newer than the
project's version, say so instead of presenting it as available. Treat "deprecated"
notes the same way: don't recommend a deprecated component or key for new work.
Where a product has a folder per major version (`/studio/2.x/...` beside
`/studio/...`; a future Rasa Pro major would get `/pro/<major>.x/...`), read the
folder that matches the project. For upgrade questions, read the matching section of
`/reference/changelogs/rasa-pro-migration-guide` (step 3).

The bundle is a snapshot from when it was downloaded, so it can predate the
project's Rasa version. This prints the newest release it knows about:

```bash
awk '$0=="Source: https://rasa.com/docs/reference/changelogs/rasa-pro-changelog"{f=1;next} f&&/^## /{print;exit}' .rasa/llms-full.txt
```

If the project runs a newer Rasa than that, refresh the bundle with
`rasa tools init docs -y` before answering.

## Lookup

**Never read either file in full.** `llms-full.txt` is ~3.4 MB (~850k tokens) and
`llms.txt` is ~53 KB; search them with the commands below. Follow the steps in
order.

### 1. Find the page in the index

```bash
# Search titles, paths, and descriptions
grep -i "slot" .rasa/llms.txt

# List every page in one area
grep "/reference/primitives/" .rasa/llms.txt
```

Each hit looks like
`- [Slots](https://rasa.com/docs/reference/primitives/slots.md): Slots are your assistant's memory.`
The page path for the next steps is the part between `/docs` and `.md`:
`/reference/primitives/slots`.

Main areas: `/reference/primitives/` (flows, flow steps, conditions, patterns,
slots, responses, actions), `/reference/config/` (`config.yml`, `domain.yml`,
components, policies, LLMs), `/reference/testing/`, `/reference/integrations/`,
`/reference/channels/`, `/reference/api/` (CLI, REST, MCP tools), `/pro/` (how-to
guides), `/learn/` (concepts), `/reference/changelogs/`. Prefer a `/reference/...`
page for exact syntax, fields, and defaults, and a `/pro/...` page for how-to
guidance.

Some descriptions are only the page's first line (e.g. "Conditions"), so a topic
word may not appear in them. Try a synonym, or list the area and pick by title,
before moving on to step 4.

### 2. Read the page

```bash
# Change only the quoted path
awk -v p="/reference/primitives/slots" \
  '$0=="Source: https://rasa.com/docs" p{f=1;print;next} f&&/^Source: /{exit} f&&++n>1000{print "[STOPPED at 1000 lines: use step 3]";exit} f' .rasa/llms-full.txt
```

This prints exactly one page, starting at its `Source:` line. Its final line may be
the following page's `#` heading — ignore it. If it prints `[STOPPED ...]`, the page
is too long to read whole: go to step 3. No output means the path did not match —
match it exactly, with a leading `/` and no trailing `/` or `.md`. Keep the awk
program in single quotes — in double quotes the shell expands `$0` before awk sees
it, and the command then returns nothing instead of failing.

### 3. Large page: list its headings, then read one section

```bash
awk -v p="/reference/primitives/patterns" \
  '$0=="Source: https://rasa.com/docs" p{f=1;next} f&&/^Source: /{print NR": [end of page]";exit} f&&/^###? /{print NR": "$0}' .rasa/llms-full.txt
sed -n '62625,63284p' .rasa/llms-full.txt
```

The first command prints each heading with its line number in `llms-full.txt`. A
section runs from its heading to the line before the next heading of the same or
higher level; the last section ends before `[end of page]`. Read the range with
`sed -n 'START,ENDp'`, or with your file-read tool's offset and limit. Always start
here for changelogs and the migration guide, which are thousands of lines long.

### 4. Not found in the index: search the full text

```bash
# Pages that mention a term, ranked by number of hits
awk -v t="minimize_num_calls" \
  '/^Source: /{u=$2; sub("https://rasa.com/docs","",u)} index($0,t){print u}' .rasa/llms-full.txt | uniq -c | sort -rn
```

Use this when the index gives no clear page, or to find where a specific config
key or class is documented. It matches the term literally and case-sensitively, and
prints page paths you can pass to step 2 or 3. Hits in `/reference/changelogs/...`
tell you *when* something changed, not how it works now: answer from the reference
or guide page, and use the changelog only for version questions.

## When the bundle is missing

If `.rasa/llms-full.txt` does not exist (the project was not set up with
`rasa tools init`, or the download failed), run `rasa tools init docs -y` in the
project root.

Failing that, use the same index-first approach online:

- https://rasa.com/docs/llms.txt is the page index; search it as in step 1.
- `https://rasa.com/docs<path>.md` serves a single page as markdown, e.g.
  https://rasa.com/docs/reference/primitives/slots.md.
- If your tools include `search_rasa_documentation` (Rasa's hosted docs MCP server,
  `https://rasa.com/docs/mcp`), you can search with it.

Do not fetch `llms-full.txt` into context, and do not answer from memory instead.
