// A dedicated worker that posts an empty message every `interval` ms, the interval its first message names. A
// hidden tab throttles its own chained timers to one wake-up a minute after five minutes; a worker's timers keep
// their cadence, so the Play screen's poll goes on every 2000 ms while the tab is hidden (AD-4, UX-DR65).

onmessage = (event: MessageEvent<number>) => {
  setInterval(() => postMessage(null), event.data)
}
