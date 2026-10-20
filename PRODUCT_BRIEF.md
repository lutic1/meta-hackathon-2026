# Product Brief: Keyframe

**Event:** Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026
**Working title:** Keyframe
**Track:** Indie developer
**Status:** Draft v3, Oct 20, 2026. This is the concept from the submitted application. Earlier drafts in this repo (Rashomon, picture-book) were wrong directions and are discarded.

## The idea

Escape rooms are magic, but they are expensive, scripted, and the same for everyone. Keyframe turns any room into a playable escape room. Photograph a room from a few angles, and about two minutes later you are walking through a 3D version of it as a game, with puzzles built from your own objects: the key behind your cactus, your books in the order only you would notice.

The game is run by a council of wizard agents, each a Muse Spark subagent:

- **The Architect** rebuilds the room from your photos using SAM 3.1 and SAM 3D Objects, and marks which objects can be interacted with.
- **The Riddler** reads what the Architect found and writes the puzzle chain and the lore around it.
- **The Guide** watches how you play, builds a persistent profile of your style across sessions, and gives hints on a ladder: nudge, then direction, then near-answer. Play twice and the Guide already knows you. It runs on Muse Glimmer locally, so play data never leaves the player's machine.
- **The Trickster** reads the same signals and adjusts difficulty mid-game, tightening or loosening the room while you are inside it.

Muse Image paints the wizard portraits and the clue cards. Muse Voice Transcribe lets the player talk to the wizards instead of typing. The whole build is done with Muse Code.

## Why it can win

Every judge has a living room. The demo puts two very different rooms side by side as two very different games, built from the same two-minute photo flow, with the wizards' private notes on each player visible to the judges. It uses the capabilities Meta is pushing hardest in this event: SAM 3.1 and SAM 3D Objects for the rebuild, Spark subagents for the game masters, Muse Image for the art, voice for the conversation, and Glimmer for on-device privacy.

## Build tiers

Ambition is staged so the demo cannot dead-end:

- **Tier 1: Myst-style scenes.** Photo scenes with interactive hotspots and the full wizard council. Playable end to end. This is the floor, and it must be demo-complete by Day 4.
- **Tier 2: True 3D.** A navigable Three.js room from the SAM 3D pipeline, with puzzles and the Guide working inside it.
- **Tier 3 (stretch): Photoreal shell.** Gaussian-splatted room as the game's skin.

## Ten-day plan

- **Day 0, Mon Oct 26:** Kickoff. API keys, cloud GPU, test rooms photographed, puzzle JSON schema fixed.
- **Day 1, Tue Oct 27:** Web app scaffold. Photo upload to SAM 3.1 to interactive-objects JSON.
- **Day 2, Wed Oct 28:** The Riddler: puzzle chain, lore, hint ladders. Tier 1 playable.
- **Day 3, Thu Oct 29:** The Guide and the Trickster: event logging, player profile, hint-rung selection.
- **Day 4, Fri Oct 30:** Voice and Muse Image wizard portraits. **Gate: record the backup demo video of Tier 1.** (Rome's soccer is 5:30 PM; plan around it.)
- **Day 5, Sat Oct 31:** SAM 3D pipeline. (Halloween. Keep the day short.)
- **Day 6, Sun Nov 1:** Three.js room standing up.
- **Day 7, Mon Nov 2:** Puzzles and the Guide working in 3D, playtest. **Gate: go or no-go on Tier 2.** If no-go, Tier 1 carries the submission.
- **Day 8, Tue Nov 3:** Second room end to end, persistent player profile across both.
- **Day 9, Wed Nov 4:** Demo video final, README, architecture diagram, submission text. **Submit early in the day.** Deadline is 9:00 PM ET.

## Architecture

- **Front end:** web app, Three.js for the 3D room, photo upload and capture flow.
- **Model layer:** this repo's provider interface. `chat` carries the Spark calls (Riddler, Guide, Trickster), `generate_image` carries Muse Image (portraits, clue cards). SAM 3.1 and SAM 3D Objects plug in as their own services behind the same boundary on Monday.
- **Guide:** runs on Muse Glimmer on the player's machine. The privacy line is a feature, not a footnote: the profile that learns how you play never leaves your device.
- **Data:** puzzle definitions as JSON against the Day 0 schema, so the Riddler's output is testable without the models live.

## Risks

- **3D quality from casual photos.** SAM 3D output from a few phone photos may not hold up. Mitigation: Tier 1 is a complete game on its own, the Day 4 gate locks a working demo video, and the Day 7 gate decides Tier 2 honestly.
- **Scope.** Four agents, voice, images, 3D, and a persistent profile in ten days with a day job. Mitigation: the tier structure. Anything past Tier 1 is additive, never load-bearing.
- **Hint quality.** A Guide that gives away answers ruins the game; one that never helps frustrates. Mitigation: the three-rung ladder is explicit in the design, and rung selection is driven by logged play events, not vibes.

## The pitch, in one paragraph

Keyframe turns any room into a playable 3D escape room in about two minutes. A council of Muse Spark wizard agents builds the room from your photos, writes puzzles from your own objects, learns how you play, and hints like it knows you, because by the second game it does. Two rooms become two different games, and no two players get the same wizards.
