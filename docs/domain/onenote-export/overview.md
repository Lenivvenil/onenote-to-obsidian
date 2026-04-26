# Bounded Context: OneNoteExport

> **DRAFT — derived from code, not from a live business interview.**
> Items marked 🔴 still require operator verification.
> Decisions already resolved by operator are integrated below.

**Purpose:** Transform a user's OneNote notebooks into Obsidian-compatible Markdown files on the local file system, preserving hierarchy, content fidelity, and supporting incremental re-export.

## Actors

- `User` — human with a personal Microsoft account who owns OneNote notebooks and an Obsidian vault
- `Microsoft Graph API` — external system; source of notebook structure and page content
- `Microsoft Identity Platform` — external system; grants access to the user's OneNote data via browser-based authorization
- `Local File System` — target; receives Markdown files, resource files, config, state, and token cache

🔴 OPEN (2026-04-26): Are there other actors? e.g. a scheduler running export automatically, a CI pipeline, Docker container runner?

## Events (past tense)

**Authentication** (owner: `AuthenticationService`):
- `AuthenticationInitiated`: User ran the CLI without a cached authorization → login prompt displayed
- `AuthenticationSucceeded`: User completed browser authorization → access token obtained and cached
- `TokenAcquiredSilently`: CLI started with a valid cached token → no browser interaction needed
- `TokenRefreshed`: Graph API rejected request with 401 → token silently renewed; request retried once
- `AuthenticationFailed`: Authorization could not complete → CLI exited with guidance message

**Enumeration** (owner: `Notebook`):
- `NotebooksListed`: Graph API returned the list of notebooks owned by the authenticated user
- `NotebookEnumerated`: All sections, section groups, and pages discovered recursively for a notebook

**Export pipeline, per Page** (owner: `Page`):
- `PageContentRetrieved`: OneNote HTML for a specific page fetched from Graph API
- `ResourcesExtracted`: Images and file attachments identified within page HTML
- `ResourceDownloaded`: A resource (image or file attachment) saved to the local Attachments Folder
- `ResourceDownloadFailed`: A resource could not be downloaded → export of the page continues with a placeholder link
- `PageConverted`: OneNote HTML transformed to Obsidian Markdown with frontmatter
- `MarkdownWritten`: Markdown file saved to the vault at the correct hierarchy path
- `PageExportErrored`: A page failed to export due to an API or file system error → logged, export continues

**Export state** (owner: `ExportState`):
- `PageSkipped`: ExportState determined page version unchanged → no fetch or write performed
- `ExportStateMarked`: Export state updated to record the page as successfully exported
- `ExportCompleted`: All selected notebooks processed; summary shown to User

**State management** (owner: `ExportState`):
- `ExportStateCleared`: User requested full re-export; all recorded page versions wiped

**Resilience** (owner: `GraphAPIClient`):
- `RateLimitEncountered`: Graph API signalled too many requests → waited the required time and retried
- `ServerErrorEncountered`: Graph API returned a server error → retried with increasing wait times

🔴 OPEN (2026-04-26): What happens when a notebook is deleted from OneNote after export? Are orphaned state entries and vault files in scope?

## Commands (imperative)

- `ExportAllNotebooks`: User → Exporter exports all notebooks to vault; mutates `ExportState`
- `ExportSpecificNotebook`: User → Exporter exports a single notebook by name; mutates `ExportState`
- `ListNotebooks`: User → Exporter enumerates and displays notebooks without writing any files
- `ClearExportState`: User → `ExportState` cleared; emits `ExportStateCleared`
- `ConfigureClientId`: User → `Config` created or updated via interactive wizard

🔴 OPEN (2026-04-26): Is there a planned `ExportSection` command (export a single section by name)?

## Aggregates

- `Notebook` (root): enforces that sections and section groups are fully enumerated before any page is exported. Populated by `ExportAllNotebooks` / `ExportSpecificNotebook` / `ListNotebooks`; emits `NotebooksListed`, `NotebookEnumerated`.
- `Page` (root of content unit): identity is `page_id` (stable); `lastModifiedDateTime` is a version attribute — a modified Page is the same Page at a new version, not a new entity. Owns its HTML content and embedded resources. Graph API is the system of record; this BC treats Page as read-only from Microsoft. Drives `PageContentRetrieved`, `ResourcesExtracted`, `ResourceDownloaded`, `ResourceDownloadFailed`, `PageConverted`, `MarkdownWritten`, `PageExportErrored`.
- `ExportState`: enforces the resume invariant — a Page whose version matches the recorded version must not be re-fetched or re-written. Determines `PageSkipped` (no fetch/write). Mutated by `ExportAllNotebooks` / `ExportSpecificNotebook` (via `ExportStateMarked`) and `ClearExportState` (via `ExportStateCleared`); emits `ExportCompleted`.
- `Config` (value object, not aggregate): the user's authorization and path settings. Created once by `ConfigureClientId` or auto-initialized on first run. No lifecycle — consumed read-only by all other aggregates.

## Domain services

- `AuthenticationService`: manages the browser authorization lifecycle. Not an aggregate (holds no domain invariants across requests). Emits `AuthenticationInitiated`, `AuthenticationSucceeded`, `TokenAcquiredSilently`, `TokenRefreshed`, `AuthenticationFailed`. Invoked by any command that requires a Graph API call.
- `GraphAPIClient`: handles all HTTP communication with Microsoft Graph API including rate-limit handling and server-error retries. Not an aggregate. Emits `RateLimitEncountered`, `ServerErrorEncountered`. Delegates token acquisition to `AuthenticationService` on 401.

🔴 OPEN (2026-04-26): Is `SectionGroup` a first-class concept (its own aggregate) or an implementation detail of OneNote's hierarchy that users don't need to name directly?

## Policies

- When Graph API returns 401 on first attempt → `TokenRefreshed`, request retried once (owner: `GraphAPIClient`)
- When `RateLimitEncountered` → wait the signalled duration, then retry the same request (owner: `GraphAPIClient`)
- When `ServerErrorEncountered` → retry with increasing wait times, up to three attempts (owner: `GraphAPIClient`)
- When `ResourceDownloadFailed` → continue export, write a placeholder link in the Markdown file (owner: `Page`) 🔴 OPEN (2026-04-26): permanent policy or workaround pending a "fail page on resource error" option?
- When `PageSkipped` → do not update ExportState (recorded version is already correct) (owner: `ExportState`)
- When `ExportStateCleared` → all subsequent Pages treated as never exported (owner: `ExportState`)

## Read models

- `NotebookTree`: consumed by `User` (via list command); shows notebook/section hierarchy with page counts; projected from `NotebookEnumerated`
- `ExportProgress`: consumed by `User` (terminal output during export); one line per Page showing position and title; projected from `PageConverted`, `PageSkipped`, `PageExportErrored`
- `ExportSummary`: consumed by `User` (terminal output at end); shows counts of exported, skipped, and errored pages; projected from accumulated `ExportStateMarked` + `PageSkipped` + `PageExportErrored`; displayed when `ExportCompleted` fires

## Boundary

- **In scope:** browser-based authorization to access the user's OneNote data; fetching notebook structure and page HTML from Microsoft; converting OneNote HTML to Markdown; downloading embedded images and file attachments; writing Markdown files and resource files to the vault; tracking which page versions have been exported
- **Out of scope:** writing back to OneNote; Obsidian plugin integration; two-way sync; export to PDF or Word; organizational or school Microsoft accounts; multi-user scenarios
- **Terms changing meaning on the edge:**
  - `Page` inside this BC = a OneNote document identified by `page_id`, with a title, two timestamps, an HTML body, and embedded resources. Outside (in Obsidian) = a Markdown `.md` file with YAML frontmatter and a local file path. Same word; inside it is a remote document with a Graph API identity, outside it is a local file.
  - `Resource` inside this BC = an embedded asset (image or file) identified by a URL on Microsoft's servers. Outside (in the vault) = a file in the Attachments Folder, identified by a local path. Same concept; inside it lives on Microsoft, outside it lives on disk.
  - `Section` inside this BC = a named container of Pages, identified by a Graph API id. Outside (in the vault file system) = a directory. Same name; inside it is an API entity, outside it is a folder.

## Ubiquitous Language

| Term | Definition (business language) | Aliases to avoid |
|---|---|---|
| `Notebook` | The top-level OneNote container owned by a user. Holds Sections and Section Groups. Exported as a top-level folder in the Vault. | "workbook", "file" |
| `Section` | A named grouping of Pages within a Notebook or Section Group. Inside this BC: an entity identified by Microsoft. In the Vault: a folder. | "folder", "tab" |
| `Section Group` | A named grouping of Sections (and nested Section Groups) within a Notebook. Inside this BC: an entity identified by Microsoft, enabling nested organization. In the Vault: a subdirectory. | "group", "folder" |
| `Page` | The atomic unit of OneNote content — a titled document with a creation date, a modification date, an HTML body, and embedded Resources. Inside this BC: identified by a stable `page_id` with a version. In the Vault: a Markdown file. | "note", "document" |
| `Resource` | An image or file that is embedded inside a Page — a photo, screenshot, PDF, or other attachment. Inside this BC: identified by a URL on Microsoft's servers. In the Vault: a file in the Attachments Folder. | "asset"; avoid bare "attachment" (ambiguous — see `File Attachment`) |
| `File Attachment` | A Resource that is a non-image file (PDF, DOCX, etc.) embedded in a Page via an object tag. A subtype of Resource. | "attachment" (use `File Attachment` when precision matters) |
| `Attachments Folder` | The per-Section subdirectory in the Vault that holds all downloaded Resources for the Pages in that Section. | "assets folder", "media folder" |
| `ExportState` | The persisted record of which Page versions have been successfully exported. Enables incremental re-export by skipping Pages whose version has not changed. | "cache", "history" |
| `Vault` | The Obsidian-managed local directory where exported Markdown files and Resource files are written. The final destination of the export. | "output folder", "target directory" |
| `Browser Authorization` | The login method this tool uses: the user visits a short URL and types a one-time code to grant the tool access to their OneNote data. No Azure account or app registration required. | "OAuth flow", "device code flow", "login" |
| `Incremental Export` | An export run that skips Pages whose version matches what was last exported, writing only new or changed Pages. Enabled by ExportState. | "resume", "delta export" |

## Context map edges

- `Microsoft Graph API` ← this BC: **Conformist** — the OneNote data model (Notebook/Section/SectionGroup/Page hierarchy, resource URLs, pagination protocol) is dictated entirely by Microsoft. This BC adapts to their schema with no negotiation power.
- `Microsoft Identity Platform` ← this BC: **Conformist** — the browser authorization protocol, token format, and error codes are external constraints this BC follows without modification.
- `Obsidian Vault` (file system output) ← this BC: **Open Host Service** — this BC produces Markdown files with YAML frontmatter and a folder hierarchy that Obsidian can read. This BC owns the output contract (frontmatter fields, folder structure, attachment paths); Obsidian is the passive consumer.

🔴 OPEN (2026-04-26): Is a future Obsidian plugin integration planned? If yes, the OHS edge may need a Published Language contract.
🔴 OPEN (2026-04-26): Are other export sources (Notion, Evernote) in scope? If yes, the Vault-writing logic may need to be extracted into a shared kernel.

## Open questions

- 🔴 (2026-04-26) Are there actors beyond the interactive User? (scheduler, CI, Docker)
- 🔴 (2026-04-26) `ResourceDownloadFailed` → placeholder link: permanent policy or future option to abort the page?
- 🔴 (2026-04-26) Is `SectionGroup` a first-class term users say out loud, or an internal OneNote detail?
- 🔴 (2026-04-26) What is the intended behavior when a Notebook is deleted from OneNote after export?
- 🔴 (2026-04-26) Are organizational (work/school) Microsoft accounts permanently out of scope?
- 🔴 (2026-04-26) Is two-way sync permanently out of scope, or a future direction?
- 🔴 (2026-04-26) Is Obsidian plugin integration planned?
- 🔴 (2026-04-26) Are other export sources (Notion, Evernote) in scope?
