// Sound (owner request Oct 30, DESIGN.md Sound): the music and the interactive sounds, every one synthesized here with
// the Web Audio API, so there is no audio file to ship or license. Nothing sounds before the first gesture, and every
// export is a quiet no-op while the sound is off, before that gesture, or where Web Audio is missing; none throws.

/** The player's choice in this browser, `on` or `off`; on when nothing is stored. */
export const SOUND_KEY = 'keyframe.sound.v1'

/** The music's two moods: the landing (a little fuller) and play (sparser, quieter). */
export type Mood = 'landing' | 'play'

export const CUES = [
  'cardHover',
  'cardChoose',
  'cardClose',
  'pageTurn',
  'trap',
  'hotspotHover',
  'knock',
  'pickUp',
  'packSelect',
  'solve',
  'chestOpen',
  'hintPinned',
  'step',
  'escape',
  'playIntro',
] as const
export type Cue = (typeof CUES)[number]

/** The tempo of the melody. */
export const BPM = 64
/** D minor pentatonic, in semitones above D. */
export const SCALE = [0, 3, 5, 7, 10]
/** The music sits well under the effects: about -26 dBFS RMS, peaks under -10 dBFS; an effect peaks at -6 dBFS at most. */
export const MUSIC_RMS_DBFS = -26
export const MUSIC_PEAK_DBFS = -10
export const EFFECT_PEAK_DBFS = -6
/** The music fades in over this long on the first gesture, and crosses from one mood to the other over this long. */
export const FADE_IN_S = 1.5
export const CROSSFADE_S = 2
/** The music fades out under a video with its sound on, and back, over this long. */
const DUCK_S = 0.8
/** The only sounds a moving pointer plays, each at most once in this many ms. */
export const HOVER_GAP_MS: Partial<Record<Cue, number>> = { cardHover: 90, hotspotHover: 250 }

const MELODY_ROOT_HZ = 293.66 // D4
const DRONE_HZ = MELODY_ROOT_HZ / 4 // D2
const BEAT_S = 60 / BPM
/** The live melody is written this far ahead of the clock, every COMPOSE_MS. */
const LOOKAHEAD_S = 1.2
const COMPOSE_MS = 300
const MUSIC_GAIN = 0.85
const EFFECT_GAIN = 1
const MOODS: Record<Mood, { gain: number; density: number; note: number; fifth: boolean }> = {
  landing: { gain: 1, density: 0.62, note: 0.055, fifth: true },
  play: { gain: 0.62, density: 0.36, note: 0.05, fifth: false },
}

/** A small seeded generator (mulberry32), so the phrases never repeat audibly and a render can be replayed. */
export function seeded(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** One sound engine on any context: the live one, or an OfflineAudioContext that renders it for a level check. */
export interface Mixer {
  /** Fades the music in to its level, or out, over `seconds`. */
  fade: (on: boolean, seconds: number) => void
  /** Fades the music out under a video with its sound on, or back, over `seconds`; the effects keep playing. */
  duck: (on: boolean, seconds: number) => void
  /** Crossfades the music to `mood` over `seconds`. */
  mood: (mood: Mood, seconds: number) => void
  /** Writes the current mood's melody up to `until` on the context's clock. */
  compose: (until: number) => void
  /** Plays `name` now, panned from -1 (left) to 1 (right). */
  cue: (name: Cue, pan?: number) => void
}

/**
 * The engine's graph on `context`: a master gain, a music bus (the two moods' drones and melodies, through its fade
 * and its duck) and an effects bus, both sending to one convolver reverb whose impulse is generated decaying noise.
 */
export function createMixer(context: BaseAudioContext, random: () => number): Mixer {
  const level = (value: number): GainNode => {
    const node = context.createGain()
    node.gain.value = value
    return node
  }
  const master = level(1)
  master.connect(context.destination)
  const reverb = context.createConvolver()
  reverb.buffer = impulse(context, 3.2, random)
  reverb.connect(master)
  const music = level(0)
  const ducker = level(1)
  music.connect(ducker)
  ducker.connect(master)
  ducker.connect(sendTo(level(0.55), reverb))
  const fx = level(EFFECT_GAIN)
  fx.connect(master)
  fx.connect(sendTo(level(0.22), reverb))
  const noise = context.createBuffer(1, context.sampleRate * 2, context.sampleRate)
  noise.getChannelData(0).forEach((_, i, data) => {
    data[i] = random() * 2 - 1
  })

  /** Ramps `param` to `value` over `seconds` from now. */
  function glide(param: AudioParam, value: number, seconds: number): void {
    const now = context.currentTime
    param.cancelScheduledValues(now)
    param.setValueAtTime(param.value, now)
    if (seconds <= 0) param.setValueAtTime(value, now)
    else param.linearRampToValueAtTime(value, now + seconds)
  }

  /** `node` out through a stereo panner at `pan` into `out`; returns `node`. */
  function panned<T extends AudioNode>(node: T, pan: number, out: AudioNode): T {
    const panner = context.createStereoPanner()
    panner.pan.value = Math.max(-1, Math.min(1, pan))
    node.connect(panner)
    panner.connect(out)
    return node
  }

  /** An envelope gain at `t`: up to `peak` in `attack` s, then an exponential decay to silence at `t + length`. */
  function envelope(t: number, peak: number, attack: number, length: number): GainNode {
    const env = context.createGain()
    env.gain.setValueAtTime(0, t)
    env.gain.linearRampToValueAtTime(peak, t + attack)
    env.gain.exponentialRampToValueAtTime(0.0001, t + length)
    return env
  }

  /** A short oscillator partial, optionally gliding from `f` to `f1`. */
  function partial(out: AudioNode, t: number, f: number, length: number, peak: number, type: OscillatorType, pan = 0, f1?: number, attack = 0.005): void {
    const osc = context.createOscillator()
    osc.type = type
    osc.frequency.setValueAtTime(f, t)
    if (f1 !== undefined) osc.frequency.exponentialRampToValueAtTime(f1, t + length * 0.6)
    const env = panned(envelope(t, peak, attack, length), pan, out)
    osc.connect(env)
    osc.start(t)
    osc.stop(t + length + 0.05)
  }

  /** Band-passed noise sweeping from `f0` to `f1`; `swell` puts the peak late, for a sound that runs backwards. */
  function sweep(t: number, length: number, f0: number, f1: number, peak: number, pan = 0, swell = false, q = 1.2): void {
    const source = context.createBufferSource()
    source.buffer = noise
    const band = context.createBiquadFilter()
    band.type = 'bandpass'
    band.Q.value = q
    band.frequency.setValueAtTime(f0, t)
    band.frequency.exponentialRampToValueAtTime(f1, t + length)
    const env = context.createGain()
    const top = t + length * (swell ? 0.85 : 0.35)
    env.gain.setValueAtTime(0.0001, t)
    env.gain.exponentialRampToValueAtTime(peak, top)
    env.gain.exponentialRampToValueAtTime(0.0001, t + length)
    source.connect(band)
    band.connect(env)
    panned(env, pan, fx)
    source.start(t, random())
    source.stop(t + length + 0.02)
  }

  /** `count` tiny high clicks scattered over `length`: a crackle or a rustle. */
  function clicks(t: number, length: number, count: number, peak: number, f = 2400): void {
    for (let k = 0; k < count; k++) {
      const at = t + random() * length
      sweep(at, 0.012 + random() * 0.02, f, f * 1.4, peak * (0.4 + random() * 0.6), random() - 0.5, false, 0.8)
    }
  }

  /** A soft low thump: a falling sine with a little noise on its front, the wax seal landing or a card setting down. */
  function thump(t: number, peak: number): void {
    partial(fx, t, 120, 0.32, peak, 'sine', 0, 48, 0.004)
    sweep(t, 0.06, 500, 220, peak * 0.4, 0, false, 0.7)
  }

  /** A bell: a sine with two inharmonic partials, a soft attack and a long tail. */
  function bell(out: AudioNode, t: number, f: number, peak: number, length: number, attack: number): void {
    for (const [ratio, amp] of [[1, 1], [2.0, 0.16], [3.01, 0.05]]) partial(out, t, f * ratio, length / ratio ** 0.4, peak * amp, 'sine', 0, undefined, attack)
  }

  /** A little pitch spread, so a repeated sound never sounds identical. */
  const vary = (f: number): number => f * (1 + (random() - 0.5) * 0.06)
  const db = (value: number): number => 10 ** (value / 20)

  const cues: Record<Cue, (t: number, pan: number) => void> = {
    cardHover: (t, pan) => sweep(t, 0.24, vary(900), vary(2800), db(-13), pan),
    cardChoose: (t) => {
      sweep(t, 0.62, vary(320), vary(2400), db(-8))
      thump(t + 1.05, db(-11))
    },
    cardClose: (t) => sweep(t, 0.5, vary(2400), vary(320), db(-5), 0, true),
    pageTurn: (t) => {
      sweep(t, 0.3, vary(3200), vary(1500), db(-12), 0.2)
      clicks(t, 0.22, 4, db(-20), 3000)
    },
    trap: (t) => {
      clicks(t, 0.7, 28, db(-17), 1800)
      thump(t + 0.55, db(-9))
    },
    hotspotHover: (t) => partial(fx, t, vary(2400), 0.05, db(-29), 'sine'),
    knock: (t) => {
      partial(fx, t, vary(190), 0.14, db(-10.5), 'triangle', 0, 130, 0.002)
      sweep(t, 0.04, 1100, 700, db(-20), 0, false, 2)
    },
    pickUp: (t) => partial(fx, t, vary(420), 0.16, db(-12), 'sine', 0, vary(980), 0.004),
    packSelect: (t) => partial(fx, t, vary(1300), 0.07, db(-19), 'triangle', 0, undefined, 0.002),
    solve: (t) => {
      bell(fx, t, vary(1174.66), db(-12.5), 1.6, 0.004)
      thump(t + 0.3, db(-11))
    },
    chestOpen: (t) => {
      const osc = context.createOscillator()
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(vary(92), t)
      for (let k = 1; k <= 6; k++) osc.frequency.linearRampToValueAtTime(vary(92 + k * 9 + (k % 2) * 14), t + k * 0.09)
      const band = context.createBiquadFilter()
      band.type = 'bandpass'
      band.frequency.value = 720
      band.Q.value = 5
      osc.connect(band)
      band.connect(envelope(t, db(-10.5), 0.08, 0.6)).connect(fx)
      osc.start(t)
      osc.stop(t + 0.65)
      partial(fx, t + 0.62, vary(2637), 0.5, db(-15.5), 'sine')
      partial(fx, t + 0.62, 3951, 0.35, db(-21.5), 'sine')
      partial(fx, t + 0.7, vary(2793), 0.45, db(-18.5), 'sine')
    },
    hintPinned: (t) => {
      sweep(t, 0.38, vary(3600), vary(2400), db(-14), -0.2, false, 0.9)
      clicks(t, 0.34, 9, db(-18), 3600)
    },
    step: (t) => sweep(t, 0.32, vary(700), vary(260), db(-7), 0, false, 0.8),
    escape: (t) => {
      // A warm fanfare chord on the effects, and a rising flourish on the music before the landing mood returns.
      for (const [k, f] of [293.66, 369.99, 440, 587.33].entries()) {
        partial(fx, t + k * 0.05, f, 2.6, db(-19), 'triangle', (k - 1.5) * 0.25, undefined, 0.06)
      }
      for (const [k, degree] of [0, 2, 3, 4, 5, 7].entries()) bell(music, t + k * 0.11, pitch(degree), MOODS.landing.note, 2.2, 0.02)
    },
    playIntro: (t) => {
      // A soft tap and a lifted bell, the curtain going up on the intro.
      partial(fx, t, vary(660), 0.08, db(-16), 'triangle', 0, undefined, 0.002)
      bell(fx, t + 0.07, vary(880), db(-17), 0.9, 0.006)
    },
  }

  /** The melody's degree `d` (0 is D4) on the scale, two octaves of it. */
  function pitch(d: number): number {
    return MELODY_ROOT_HZ * 2 ** ((SCALE[d % SCALE.length] + 12 * Math.floor(d / SCALE.length)) / 12)
  }

  /** A mood's bus with its drone: two slightly detuned oscillators (and a fifth on the landing) through a slow low-pass. */
  function moodBus(mood: Mood): GainNode {
    const bus = level(0)
    bus.connect(music)
    const filter = context.createBiquadFilter()
    filter.type = 'lowpass'
    filter.frequency.value = 380
    filter.Q.value = 0.6
    const lfo = context.createOscillator()
    lfo.frequency.value = 0.045
    const depth = level(150)
    lfo.connect(depth)
    depth.connect(filter.frequency)
    const drone = level(0.07)
    filter.connect(drone)
    drone.connect(bus)
    const voices: [number, number][] = [[DRONE_HZ, 1], [DRONE_HZ * 1.0035, 1], ...(MOODS[mood].fifth ? [[DRONE_HZ * 1.5, 0.45] as [number, number]] : [])]
    for (const [f, amp] of voices) {
      const osc = context.createOscillator()
      osc.type = 'triangle'
      osc.frequency.value = f
      const g = level(amp)
      osc.connect(g)
      g.connect(filter)
      osc.start()
    }
    lfo.start()
    return bus
  }

  const buses: Record<Mood, GainNode> = { landing: moodBus('landing'), play: moodBus('play') }
  let current: Mood = 'landing'
  const melody = { next: 0, degree: 4, left: 0 }

  /** One step of the melody at `t`: a note (or a rest) on a phrase's random walk; returns the time to the next step. */
  function step(t: number): number {
    const spec = MOODS[current]
    if (melody.left <= 0) {
      melody.left = 3 + Math.floor(random() * 5)
      return BEAT_S * (2 + Math.floor(random() * 3)) // a breath between phrases
    }
    melody.left -= 1
    if (random() > spec.density) return BEAT_S
    const moves = [-2, -1, -1, 0, 1, 1, 2]
    melody.degree = Math.max(0, Math.min(9, melody.degree + moves[Math.floor(random() * moves.length)]))
    bell(buses[current], t, pitch(melody.degree), spec.note, 3.2, 0.03)
    if (spec.fifth && random() < 0.18) bell(buses[current], t, pitch(Math.max(0, melody.degree - 5)) / 2, spec.note * 0.7, 3.6, 0.05)
    return random() < 0.18 ? BEAT_S / 2 : BEAT_S
  }

  return {
    fade: (on, seconds) => glide(music.gain, on ? MUSIC_GAIN : 0, seconds),
    duck: (on, seconds) => glide(ducker.gain, on ? 0 : 1, seconds),
    mood: (mood, seconds) => {
      current = mood
      for (const name of ['landing', 'play'] as const) glide(buses[name].gain, name === mood ? MOODS[name].gain : 0, seconds)
    },
    compose: (until) => {
      melody.next = Math.max(melody.next, context.currentTime + 0.05)
      while (melody.next < until) melody.next += step(melody.next)
    },
    cue: (name, pan = 0) => cues[name](context.currentTime + 0.01, pan),
  }
}

/** `node` into `out`; returns `node`. */
function sendTo(node: GainNode, out: AudioNode): GainNode {
  node.connect(out)
  return node
}

/** A stereo impulse of decaying noise, `seconds` long: the room the sounds ring in. */
function impulse(context: BaseAudioContext, seconds: number, random: () => number): AudioBuffer {
  const length = Math.round(context.sampleRate * seconds)
  const buffer = context.createBuffer(2, length, context.sampleRate)
  for (let channel = 0; channel < 2; channel++) {
    const data = buffer.getChannelData(channel)
    for (let i = 0; i < length; i++) data[i] = (random() * 2 - 1) * Math.exp((-4.5 * i) / length)
  }
  return buffer
}

// ---- the live engine: one lazily created AudioContext on the first gesture ----

let enabled = readSoundOn()
let context: AudioContext | undefined
let mixer: Mixer | undefined
let mood: Mood = 'landing'
let ducked = false
let started = false
const lastHover = new Map<Cue, number>()

/** The stored choice; on when nothing is stored or storage is refused. */
export function readSoundOn(): boolean {
  try {
    return localStorage.getItem(SOUND_KEY) !== 'off'
  } catch {
    return true
  }
}

/** Whether the sound is on in this browser. */
export function soundOn(): boolean {
  return enabled
}

/** Turns the sound on or off and remembers it; off suspends the context, on (a gesture) wakes it. */
export function setSoundOn(on: boolean): void {
  enabled = on
  try {
    localStorage.setItem(SOUND_KEY, on ? 'on' : 'off')
  } catch {
    // storage refused: the choice holds for this page load
  }
  if (!on) void context?.suspend().catch(() => undefined)
  else wake()
}

/** The first gesture creates the context (browsers refuse sound before one); a later one resumes it. */
function wake(): void {
  if (!enabled || typeof document === 'undefined' || document.hidden) return
  try {
    if (context === undefined) {
      const Context = globalThis.AudioContext as typeof AudioContext | undefined
      if (Context === undefined) return
      const live = new Context()
      const mix = createMixer(live, seeded(Date.now()))
      context = live
      mixer = mix
      mix.mood(mood, 0)
      mix.duck(ducked, 0)
      mix.fade(true, FADE_IN_S)
      setInterval(() => {
        if (live.state === 'running') mix.compose(live.currentTime + LOOKAHEAD_S)
      }, COMPOSE_MS)
    }
    if (context.state !== 'running') void context.resume().catch(() => undefined)
  } catch {
    // Web Audio refused: the page stays silent
  }
}

function onVisibility(): void {
  if (context === undefined) return
  if (document.hidden) void context.suspend().catch(() => undefined)
  else if (enabled) void context.resume().catch(() => undefined)
}

/** The music fades out while any video on the page plays with its sound on, and comes back when none does. */
function onMedia(): void {
  const sounding = [...document.querySelectorAll('video')].some(
    (video) => !video.paused && !video.ended && !video.muted && video.volume > 0,
  )
  if (sounding === ducked) return
  ducked = sounding
  mixer?.duck(sounding, DUCK_S)
}

/** Listens for the first gesture, the tab hiding and the page's videos; once per page load. */
export function startSound(): void {
  if (started || typeof document === 'undefined') return
  started = true
  document.addEventListener('pointerdown', wake, true)
  document.addEventListener('keydown', wake, true)
  document.addEventListener('visibilitychange', onVisibility)
  // Media events do not bubble; a listener on the document's capture path hears every video.
  for (const event of ['play', 'playing', 'pause', 'ended', 'volumechange', 'emptied']) document.addEventListener(event, onMedia, true)
}

/** Crossfades the music to `next` (the shell calls it on every route). */
export function setMood(next: Mood): void {
  mood = next
  try {
    mixer?.mood(next, CROSSFADE_S)
  } catch {
    // the context is gone: silent
  }
}

/** Plays sound `name`, panned by `pan`; the two hover sounds are throttled (`HOVER_GAP_MS`). */
export function cue(name: Cue, pan = 0): void {
  if (!enabled || mixer === undefined || context?.state !== 'running') return
  const gap = HOVER_GAP_MS[name]
  const now = performance.now()
  if (gap !== undefined && now - (lastHover.get(name) ?? -Infinity) < gap) return
  if (gap !== undefined) lastHover.set(name, now)
  try {
    mixer.cue(name, pan)
  } catch {
    // a node the context refused: this one sound is skipped
  }
}
