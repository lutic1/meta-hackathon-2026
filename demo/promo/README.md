# Keyframe inspiration sequence

An optional recording aid for the demo script: Netflix interactive games inspired the idea of turning your own room into a game. This independent promotional concept is not a Netflix integration or affiliation.

## Preview

From the repository root:

```sh
python3 -m http.server 8765
```

Open `http://localhost:8765/demo/promo/` in a desktop browser. No build or credentials are needed. The catalog and videos work locally; entering the live site requires internet access.

## Sequence

1. The supplied **The Conjuring: Unspoken** screenshot is featured for five seconds.
2. A 0.9-second dissolve reveals the generated Keyframe hero.
3. Two seconds after that dissolve finishes, the existing Keyframe tutorial plays muted and loops inside the hero.
4. **Play Game** opens the live Keyframe site in a frame while replaying the original opening video. **Enter Keyframe** reveals the live site. **Open site** opens it directly if framing is unavailable.

Use **Replay preview** or **R** to restart the catalog sequence. Clicking The Conjuring skips ahead to the Keyframe reveal. **More Info** explains the concept; other titles are reference cards, not playable integrations.

The launcher replays the intro on every entry and adds a fresh query parameter to the live URL. It does **not** clear browser cache, cookies, or the live site's local storage. On a first visit the live site may also show its own intro. Its existing replay/seen behavior is unchanged. The live destination is the `LIVE` constant in `promo.js`.

## Assets and provenance

- `web/public/promo/netflix.png` and `netflix-rows.png`: user-supplied Netflix screenshots used to illustrate the inspiration; third-party game artwork and marks remain their owners'.
- `web/public/promo/keyframe-hero.png`: promotional concept art generated with OpenAI's built-in image-generation tool for this sequence; see `hero-prompt.txt`. It is not gameplay or a Meta-model output.
- Intro and tutorial videos and the intro poster reuse `web/public/intro/` and `web/public/tutorial/`; no duplicate videos are stored here.

The promo is separate from the product entry point and does not change the game's behavior. It is intended to accompany the spoken inspiration segment, followed by the actual working product.
