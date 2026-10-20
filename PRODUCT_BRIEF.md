# Product Brief: Picture-Book Any Document

**Event:** Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026
**Theme:** Build for Your World
**Status:** Draft v2, Oct 20, 2026. Replaces v1 (wrong direction, discarded). Concept as submitted in the application.

## The problem

The documents that matter most are the ones people cannot read. A benefits plan, an immigration guide, a medical leaflet: hundreds of pages of dense text, written for lawyers and administrators, handed to people who need the information most and are least equipped to get through it. Low-literacy adults, newcomers working in a second language, and kids fall out at page one. The information exists. It just never reaches them.

## The product

Drop in a long PDF, up to 200 pages. Get back a 20-panel illustrated picture book that tells the same content as a story, in the reader's language, at the reader's reading level, with one consistent guide character who walks through every panel.

The reader picks two things: language and reading level. Everything else is the system's job: decide what matters in the document, turn it into a story a person can follow, and draw it.

Working cost assumption from the concept: at roughly $0.01 per generated image, a 20-panel book costs about 20 cents in image generation. Verify against actual Muse Image pricing at kickoff.

## How it works

1. **Read the whole document.** Muse Spark's 1M-token context takes in the full PDF text, so the story is planned against the complete document, not chunks that lose the thread.
2. **Plan the story.** The model selects the points a reader must walk away with and writes a 20-panel script: one idea per panel, plain language, at the requested reading level, in the requested language.
3. **Fix the guide character.** Before any panel is drawn, the system generates the guide character once and locks a written character spec: appearance, clothing, colors, style. That spec and the reference image go into every panel prompt. Character consistency across 20 panels is the product's hardest problem and its most visible feature.
4. **Draw the panels.** Muse Image generates each panel from its script line plus the locked character spec.
5. **Assemble the book.** Panels and captions come out as a readable, printable, shareable picture book.

## Why this fits

Build for Your World asks for a problem you know firsthand. Benefits documents are my day job's raw material, and immigration paperwork is my own family's history. The demo is also honest about what it is: show a page nobody can read, then show the same content as a panel a child can follow. Thirty seconds, no explanation needed.

## Scope for ten days

**Must ship (MVP by Nov 1):**
- PDF in, text extracted, full-document story plan out
- Language and reading level controls that visibly change the output
- 20 generated panels with the guide character consistent across them
- Assembled picture book (web view plus PDF export)
- One polished demo end to end: a real benefits plan or immigration guide, converted live

**Should ship (Nov 2 to 3):**
- Second demo document in a second language
- Reading-level comparison view: same document at two levels, side by side

**Stretch:**
- Panel-level regeneration (redraw one panel without rebuilding the book)
- Audio narration of the captions

**Explicitly out of scope:**
- Documents beyond roughly 200 pages in the demo path
- Perfect factual coverage of every clause. The product is a faithful summary with a story spine, and the submission will say so plainly.

## Demo plan

Ninety seconds. Show the source document first: one dense page of a benefits plan, small print, no pictures. Then run the conversion. Show the book: the guide character explaining the same content across panels a newcomer can actually read. Switch the language live and redraw one panel. End on cost: the whole book for about 20 cents of image generation (pending price verification at kickoff).

Choose the showcase documents in advance and rehearse with them. Per the concept notes, avoid demos that need perfect accuracy: pick inputs the system handles well, record the demo video early, and build fallbacks so nothing stalls on stage.

## Risks

- **Character consistency.** Twenty panels, one character, and image models drift. Mitigation: locked character spec plus reference image in every prompt, a consistency check pass on the panel set, and per-panel regeneration as the fallback.
- **Reading-level control.** Models write above the target level unless pushed. Mitigation: level-specific instructions and a plain-language pass before drawing.
- **API unknowns.** The Meta Model API surface is not public until kickoff. Mitigation: the app is built against a provider interface with a mock backend, so Monday's work is one client implementation, not a rewrite.

## Timeline

- **Oct 26:** Kickoff. Wire the Meta Model API client. Verify Muse Image pricing and character-reference support.
- **Oct 27 to 29:** Ingest, story planner, and panel pipeline working end to end on the mock, then on live models.
- **Oct 30 to Nov 1:** Character consistency hardening, language and reading level controls. MVP freeze Nov 1.
- **Nov 2 to 3:** Second demo document, demo video recorded.
- **Nov 4:** Submission package complete by 6 PM ET. Deadline is 9 PM ET.
