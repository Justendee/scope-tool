# Project Context: AI Assisted Scope Management Tool
# Scott Construction | BCIT CMGT 8800 Capstone | Justen Dekam

---

## Company Entity Names
The tool generates documents under different Scott Construction entity
names depending on the project. A checkbox in the UI selects which
entity name appears on all generated outputs for that project.

Options:
- SCOTT Construction Ltd.
- SCOTT Special Projects Ltd.
- Scott DB Services Ltd.
- SCOTT Construction Management Ltd.
- SCOTT Construction (Ontario) Inc.

The selected entity name is used in the Appendix B header and any
other generated documents requiring a company name.

---

## Project Types
A checkbox in the UI selects the project type. This selection
influences scope assignment rules, missing document detection, and
lessons learned filtering at Phase 3.

Options:
- Commercial
- Residential
- Industrial
- Special Projects
- COV (City of Vancouver)

COV projects use specific client conventions visible in the CAR
template: TO field is "The City of Vancouver", templates follow
COV formatting standards.

---

## What This Tool Does
This is a web application that uses the Anthropic Claude API to assist
Scott Construction's estimating team with scope management tasks during
pre-construction. It reads project drawings and specifications and
produces structured scope documents in Scott Construction's internal
formats.

---

## Tech Stack
- Python
- Streamlit (web UI framework)
- Anthropic Claude API (claude-sonnet-4-6 by default)
- PyMuPDF (PDF text extraction and page rendering)
- python-dotenv (API key management)
- openpyxl (Excel file generation for CAR output)

---

## Three Core Workflows
The tool has three workflows accessed via three buttons in the UI.
The CAR award recommendation has been removed. The estimator reviews
the populated CAR and makes the award decision using their own
judgment and knowledge. The AI does not generate dollar amounts for
missing scope or make award recommendations.

1. Generate Scope: runs drawing indexing and spec extraction together
   in one step. The estimator labels each uploaded PDF as Drawings,
   Specifications, Statement of Work, Hazmat Report, or Other.
   Drawing files go through Phase 1 image processing. Spec files go
   through Phase 2 text extraction. Both outputs save to the project
   folder as drawing_index.json and scope_summary.txt and persist
   between sessions.
2. Generate Appendix B: uses the stored drawing index and spec
   summary to produce the Appendix B Word document for the selected
   trade or division.
3. Populate CAR: reads uploaded trade quotes, maps inclusions and
   exclusions against Appendix B scope items, and populates the CAR
   Excel tab for the selected trade. The AI flags scope gaps and
   discrepancies between bidders but does NOT generate dollar amounts
   for missing scope. Subtotal B exclusion rows have descriptions
   filled in but dollar amounts left blank for the estimator to price.
   Subtotal C associated work rows are also left blank for the
   estimator. This workflow is not yet built.

---

## Division Tabs (CAR Tabs and Corresponding Appendix B Scopes)
The following tabs are the ones the AI works with. Tabs before
2. Demolition and after 16. Electrical are completed manually by
estimators and must not be modified by the tool.

  2. Demo and Abatement
  2. Demolition
  2. Excavating
  2. Landscaping
  3. Concrete Works
  4. Masonry
  5. Steel
  6. Framing
  6. Millwork
  7. Roofing
  7. Cladding
  8. Doors
  8. Glazing
  9. GWB
  9. Flooring
  9. Paint
  14. Conveying Systems
  15. Mechanical
  16. Electrical

Each of these tabs has an identical structure. When generating
Appendix B documents, one document is produced per tab. The scope
items in the Appendix B for a given trade must correspond directly
to the scope inclusion lines in that trade's CAR tab.

---

## Output File Naming Conventions
Generated files follow the naming conventions observed in completed
project files.

Appendix B (Word document):
  [Project#] - [Project Name] - Appendix B - [Subcontractor Name].docx
  Example: 5246 - Marpole Library - Appendix B - Lincor.docx
  If no subcontractor name is entered, Trade or Division is used.

CAR (Excel workbook):
  [Project#] - [Project Name] - LIVE.xlsx
  Example: 5246 - Marpole Library Expansion R1 - LIVE.xlsx

File names use spaces not underscores. The project number and project
name are entered at project setup. The Subcontractor Name field is
left blank until contract award. The Trade or Division dropdown
selects which trade the document is being generated for.

---

## Estimator Notes Fields
The UI includes two levels of estimator notes that provide context
to the AI during scope generation. Notes are editable at any time
and are displayed in the UI before each workflow run so the
estimator can review and confirm what context the AI is working
with.

### Project Level Notes
A single free text field that applies to the entire project.
Used for high level instructions that affect all trades.

Examples:
- "Phase 1 only. Exclude all Phase 2 work shown on drawings."
- "Assume tenant fitout by others. Base building scope only."
- "Owner is supplying all mechanical equipment. Include install
  only for mechanical trades."

Project level notes are injected into every scope generation
prompt for the project automatically.

### Division Level Notes
A free text field per division tab. Used for trade-specific
instructions that override or qualify what is shown on drawings
for that trade only.

Examples:
- Framing tab: "Exterior framing is in a separate contract.
  Include interior framing only."
- Electrical tab: "EV charging rough-in is excluded from this
  project. Do not include in scope even if shown on drawings."
- Paint tab: "Intumescent painting is a separate specialty
  contract. Exclude from this scope even if shown on drawings."

Division level notes are injected only into the prompt for that
specific division and do not affect other trades.

### Prompt Injection Format
When notes are present they are injected into the prompt with
clear framing so the AI treats them as overriding instructions:

"ESTIMATOR NOTES FOR THIS PROJECT: [project level notes]

ESTIMATOR NOTES FOR THIS TRADE: [division level notes]

These notes take priority over anything shown on the drawings or
specifications. If a note says to exclude something, do not
include it in the scope even if it appears on the drawings."

---

## Three Phase Document Processing Architecture
Construction drawing sets are too large to send to the API in one
call. The system processes documents in three sequential phases.

### Phase 1: Drawing Index
- Export drawing sheets as high resolution images (5 to 10 sheets
  per API call)
- Each batch: identify sheet number, discipline, title, revision,
  trades referenced, scope notes, schedules, interface conditions,
  and cross-references to other documents
- Store results in a structured JSON index file
- Index is generated once per project and reused for all workflows
- Cross-references detected in drawings (e.g. "refer to structural
  drawings for footing details") are logged so the system can flag
  if the referenced document is absent from the uploaded package

### Phase 2: Specification Parsing
- Process specs as text, division by division (CSI MasterFormat)
- Extract scope requirements, submittal obligations, coordination
  requirements, and associated work items per division
- Apply scope assignment rules file to allocate work to correct
  trades. Example: blocking specified under a mechanical division
  is assigned to rough carpentry scope
- Scope assignment rules are refined across projects as part of
  continuous improvement

### Phase 3: Scope Assembly
- Query drawing index for sheets relevant to each target trade
- Retrieve only those sheets for detailed review (15 to 20 sheets
  per trade, not full set)
- Combine drawing content, specification content, scope assignment
  rules, and lessons learned distilled rules
- Produce Appendix B scope document for the trade
- Same scope items used to pre-populate the CAR tab for that trade

---

## Missing Information Detection
The system uses a two-tier detection approach.

### Tier 1: Statement of Work Inference
If a form of statement of work or project brief is uploaded, the
system reads it to infer what documents should be present for that
project scope. For example, if the statement of work references
dewatering, a geotechnical report should be present. If it
references a green roof, a landscape drawing set should be present.
The system flags any document referenced in the statement of work
that is not present in the uploaded package.

### Tier 2: Drawing Cross-Reference Detection
During Phase 1 drawing indexing, the system logs every instance
where a drawing references another document. Examples:
- "Refer to geotechnical report for bearing capacity"
- "See structural drawings S-series for footing details"
- "Refer to MEP coordination drawings"

If a referenced document is not present in the uploaded package,
the system flags it as absent with a note identifying which drawing
made the reference and what was expected.

### Tier 3: Fixed Fallback Checklist
When no statement of work is provided, the system applies a default
checklist based on project type. Documents flagged as typically
required:
- Geotechnical report
- Civil and site drawings
- Structural drawings
- Mechanical drawings
- Electrical drawings
- Full specification package
- Fire protection drawings
- Landscape drawings (project type dependent)

All missing document flags are surfaced in the UI before scope
generation proceeds so the estimator can decide whether to proceed
with incomplete information or obtain the missing documents first.

---

## Appendix B Document Structure
Every generated Appendix B must follow this exact structure.
Do not deviate from it.

### Header
- Underlined title: Contract # [number] -- [Trade Name]
- Bold preamble: "In addition to the scope of work indicated in the
  Contract Documents, the Contract Scope of Work includes but is
  not limited to:"
- Bold division reference: "Division -- [CSI number / section]"

### Item 1: Scope Reference (do not modify)
References Division 1, the relevant specification section(s) for
this trade, and related sections.

### Item 2: General Scope of Work heading (do not modify)

### Items 3 to 55: General Scope of Work (do not modify)
Fixed boilerplate block covering supervision, safety, submittals,
Procore, scheduling, and contract administration. Never change,
add to, or delete any item in this section.
- Item 6 (LEED clause): strike through when not applicable
- Item 20 (tower crane clause): strike through when not applicable

### Item 56: Specific Scope of Work (AI fills this section)
Format:
  56. Provide all labour, materials, and equipment to supply and
      install [trade description] in accordance with drawings and
      specifications, including, but not limited to:

      56.1  [specific scope item]
      56.2  [specific scope item]
      (continue as needed)

Rules:
- All sub-items use 56.x numbering only. Never use 57.1 etc.
- Favour more separate lines over long single items
- Items must be project-specific based on drawings and specs
- Capture all major scope items shown on drawings
- Language must be direct and construction-specific
- Write item descriptions so they can be used as CAR inclusion
  rows for this trade without rewording

### Item 57: Supervision and First Aid (do not modify)
Fixed item covering WorkSafeBC supervision requirements.

### Scope of Work Exclusions (AI fills when quotes are received)
- Numbered sequentially from 58 onward
- Short clear statements of what is not included
- Sourced from trade quotes after pricing is received
- Leave as placeholder on initial Appendix B generation before
  quotes are received

### Scheduling of Work (do not modify)
Fixed: "As per attached Appendix D Project Schedule"

### Contract Administration (do not modify)
Fixed block covering progress claims, insurance, charge-out rates,
WSBC clearance, and holdback release.

---

## Appendix B Generation Prompt
Use this prompt logic when generating an Appendix B:

"Fill in the Specific Scope of Work in the attached Appendix B for
[trade name] for this project. Add project-specific scope items
based on the drawings and specifications. Do not change, modify,
or delete any items in the General Scope of Work section. All
sub-items must use 56.x numbering only. Never use 57.1 or other
parent item numbers. Favour splitting scope into more separate
lines rather than long single items. Ensure all major scope items
are captured. Write item descriptions in plain construction
language that can be used directly as inclusion check rows in the
CAR Excel tab for this trade. Leave the Scope of Work Exclusions
section blank for completion after trade quotes are received."

---

## CAR Excel Tab Structure (Per Division Tab)
Every division tab follows this exact structure. The AI populates
only designated fields and never modifies fixed structural elements.

### Header Block
Fixed fields: project name, client, attention, estimator, date,
division description, budget amount. Populated at project setup
from UI inputs.

### Tender Results Block

**SUBTRADE PRICE INCLUSIONS (Subtotal A)**
- First data row: lump sum bid price per bidder (up to 4 bidders,
  fixed columns K, L, M, N)
- Subsequent rows: selected scope check items per the CAR line item
  selection logic below
- Each row: description in column C, Included / Not Included /
  dollar value per bidder column
- Subtotal A: sum of base prices

**ESTIMATED PRICE ADJUSTMENTS FOR SCOPE EXCLUSIONS (Subtotal B)**
- Items excluded by one or more bidders from their lump sum price
- Dollar value entered per bidder to normalize the exclusion
- Levels all bids to an apples-to-apples adjusted total
- Subtotal B: sum of exclusion adjustments

**ASSOCIATED WORK (Subtotal C)**
- Work required for this division scope that no bidder included
- Priced separately and applied equally across all bids
- Subtotal C: sum of associated work items

**ADJUSTED TOTAL**
- Subtotal A plus Subtotal B plus Subtotal C per bidder
- This is the leveled comparable total used for award decisions

### Comments Section
- Left blank for the estimator to complete
- The AI does not generate award recommendations
- The estimator reviews the populated CAR and makes the award
  decision using their own judgment and market knowledge

---

## CAR Line Item Selection Logic
The CAR inclusion rows are not a copy of all Appendix B 56.x items.
The Appendix B is the detailed scope document. The CAR is a leveling
tool. The AI applies the following judgment when selecting CAR line
items.

### Include as Subtotal A line items:
- Major scope items that confirm the bulk of the work is priced.
  Example from GWB tab: each ceiling type listed by type reference
  (C1, C2, C3 etc.), steel stud walls, GWB assemblies, seismic
  engineering
- Items where trades commonly split supply and install into separate
  prices. List supply and install as separate rows so gaps are
  immediately visible. Example from Doors tab: wood door and frame
  supply, wood door and frame install, hardware supply, hardware
  install are all separate rows because different trades priced
  these differently
- Project-specific items an estimator needs confirmed. Example from
  Paint tab: intumescent paint on columns, MPI inspection and
  guarantee
- PST inclusion: always include as a line item

### Include in Subtotal B (Scope Exclusions):
- Any item where at least one bidder excluded it from their lump
  sum. Read quotes and identify gaps, then add a normalized dollar
  value so the bid can be leveled
- Example from Paint tab: intumescent paint was priced below the
  line by all three trades and needed a separate adjustment
- Example from GWB tab: millwork backing excluded by two of three
  trades required a $25,000 adjustment to level

### Include in Subtotal C (Associated Work):
- Work clearly required for this division that no bidder included
- Work at a trade boundary being carried separately by the GC
- Example from Paint tab: touch-ups, finish protection, misc
  caulking priced uniformly and added as associated work
- Example from Doors tab: closures for existing glazing, door
  backing and misc materials, additional door in PTA1

### Do not include as CAR line items:
- Detailed procedural items implied by the lump sum (surface
  preparation, protection of adjacent surfaces, mobilizations)
- Administrative items (submittals, warranties, maintenance
  materials) unless a specific trade is known to exclude these
- Items already captured under a broader line item

---

## Trade Quote Input Formats
Trade quotes arrive in two formats:

- PDFs with itemized inclusions and exclusions lists
- Emails with a lump sum price and brief notes

The AI handles both. For PDF quotes, extract the lump sum,
inclusions list, and exclusions list. For email quotes, extract
the lump sum and any noted qualifications. Map both against the
Appendix B scope items to determine Included, Not Included, or
dollar value status for each CAR line item.

---

## Lessons Learned Repository
The system uses a two-tier structure to capture and apply
institutional knowledge over time.

### Tier 1: Raw Notes (estimator-facing)
Estimators log corrections ad hoc whenever they notice the AI
output needs improvement. Logging is done directly in the app
with minimal friction. Each note captures:
- Date
- Project number
- Trade or division
- Project type
- Plain language description of what was wrong and what it
  should have been

Example note:
"Cladding scope for commercial project combined panel supply,
flashing, and sealant into one line. Should always be three
separate items."

Raw notes are stored as JSON in notes_raw.json.

### Tier 2: Distilled Rules (AI-facing)
Periodically, accumulated raw notes are reviewed and distilled
into clean rules. This review is done by the user with Claude's
assistance. Each distilled rule captures:
- Rule ID
- Trade or division
- Project type (or "all" if universal)
- Rule description in plain language
- Tag: one of scope_gap, wrong_trade_assignment, missing_item,
  language_preference, split_required
- Date added
- Source note IDs that generated this rule

Example distilled rule:
{
  "rule_id": "R001",
  "trade": "Cladding",
  "project_type": "all",
  "rule": "Always split cladding scope into separate line items
           for panel supply, flashing supply, and sealant rather
           than combining into a single item.",
  "tag": "split_required",
  "date_added": "2026-04-01",
  "source_notes": ["N003", "N007"]
}

Distilled rules are stored as JSON in rules_distilled.json and
are injected into the Phase 3 scope assembly prompt for the
relevant trade and project type.

---

## Benchmarking
Evaluated against:
1. Manual process (current state at Scott Construction)
2. Provision (commercial AI platform Scott Construction is trialing)

Comparison metrics: time per workflow, scope accuracy, gap
detection rate, cost per project.

Custom tool target cost: $5 to $15 USD per project in API usage.
Provision cost: approximately $4,000 to $5,000 USD per project.

---

## API Cost Guidelines
- Use claude-sonnet-4-6 by default for all API calls
- Reserve claude-opus-4-6 for prompt design and complex judgment
  tasks only
- Drawing index phase: approximately $0.50 to $1.00 USD per 100
  sheet project (10 to 15 API calls)
- Index is generated once per project and reused for all subsequent
  workflow runs

---

## Data Security
- API key stored in .env file, never committed to GitHub
- Prototype hosted locally during development and testing
- No real project data on publicly accessible servers
- .env must be listed in .gitignore before first commit

---

## Project Management System
Each project gets its own subfolder under projects/ named by project
number. All generated files for that project save into its folder.

Folder structure:
  projects/
    5246/
      project_info.json  (project number and name)
      drawing_index.json (Phase 1 output, reused across sessions)
      scope_summary.txt  (Phase 2 output, reused across sessions)

On startup the app scans the projects/ folder and populates a Load
Existing Project dropdown. Selecting a project and clicking Load
restores the project number, name, drawing index, and scope summary
into session state.

New Project clears all project session state except entity and
project type checkboxes which persist.

Delete Project shows a confirmation dialog requiring the user to
type DELETE (case sensitive) before the project folder and all its
contents are permanently removed. Deleted project numbers are stored
in a session-level recently deleted set to prevent the folder from
being recreated by stale widget state during the same session.

---

## UI Layout and Sidebar Order
Sidebar top to bottom:
1. Project Number input
2. Project Name input
3. Load Existing Project dropdown with Load button
4. New Project button
5. Delete Project button (only shown when a project is loaded)
6. Divider
7. Entity Name checkboxes (mutually exclusive)
8. Project Type checkboxes (mutually exclusive)
9. Divider
10. Trade or Division dropdown (19 options matching CAR tabs)
11. Subcontractor Name input (used in filename at award only)
12. Divider
13. Project Level Notes text area
14. Division Level Notes text area

Main panel:
- Multi-file PDF uploader with file type selector per file
  (Drawings, Specifications, Statement of Work, Hazmat Report, Other)
- Three action buttons: Generate Scope, Generate Appendix B,
  Populate CAR
- Output display area showing generated content
- Download buttons appear after successful generation

---

## Division Verb Phrase Lookup
Each division uses a specific verb phrase in the item 56 intro
sentence. The lookup table is:

  2. Demo and Abatement    -> complete
  2. Demolition            -> complete
  2. Excavating            -> complete
  2. Landscaping           -> complete
  3. Concrete Works        -> complete
  4. Masonry               -> supply and install
  5. Steel                 -> supply and install
  6. Framing               -> supply and install
  6. Millwork              -> supply and install
  7. Roofing               -> supply and install
  7. Cladding              -> supply and install
  8. Doors                 -> supply and install
  8. Glazing               -> supply and install
  9. GWB                   -> supply and install
  9. Flooring              -> supply and install
  9. Paint                 -> supply and application of
  14. Conveying Systems    -> supply and install
  15. Mechanical           -> supply and install
  16. Electrical           -> supply and install

For "supply and application of" trades the sentence reads:
"Provide all labour, materials and equipment for the supply and
application of [intro_text], in accordance with drawings and
specifications, including, but not limited to:"

For all other trades:
"Provide all labour, materials and equipment to [verb] [intro_text],
in accordance with drawings and specifications, including, but not
limited to:"

---

## Project Status
Update this section at the start of each Cursor session.
Current phase: [ ]
Last working feature: [ ]
Next task: [ ]
Known issues: [ ]
