# NNNN. {Short decision title in imperative mood}

* Status: {proposed | accepted | deprecated | superseded by [NNNN](NNNN-*.md)}
* Date: {YYYY-MM-DD}
* Deciders: {list of people involved in the decision}
* Tags: {comma-separated, e.g. architecture, security, tooling}

## Context and Problem Statement

{Describe the context and problem statement. Why now? What forces are in play? Two to four sentences, not a history lesson.}

## Decision Drivers

* {driver 1 — concrete, measurable where possible}
* {driver 2}
* {driver 3 — minimum three, otherwise you haven't thought enough}

## Considered Options

* {Option A}
* {Option B}
* {Option C — minimum three, strawmen excluded}

## Decision Outcome

Chosen option: **{Option X}**, because {one-paragraph justification referencing the drivers; cite `docs/principles.md` if any principle is invoked}.

### Positive Consequences

* {good thing 1}
* {good thing 2}

### Negative Consequences

* {bad thing 1 — if Bad < Good, you're rationalizing, redo}
* {bad thing 2}
* {bad thing 3 — aim for Bad ≥ Good}

## Pros and Cons of the Options

### {Option A}

* Good, because {...}
* Good, because {...}
* Bad, because {...}
* Bad, because {...}

### {Option B}

* Good, because {...}
* Bad, because {...}

### {Option C}

* Good, because {...}
* Bad, because {...}

## Confirmation

{How will the decision be validated? Concrete mechanism — not "we will monitor". Example: "Run `/usage` weekly; if advisor Opus tokens exceed 5% of weekly cap, reopen this decision."}

## Re-visit Trigger

{Concrete falsifiable condition under which this decision should be reconsidered. Example: "When GitHub Projects v2 adds native burndown" or "When team exceeds 3 developers" or "When Opus 5 launches." If you cannot write a trigger, the decision is not a decision.}

## Links

* {Related ADRs: supersedes, superseded by, related to}
* {External references — docs, blog posts, RFCs}
