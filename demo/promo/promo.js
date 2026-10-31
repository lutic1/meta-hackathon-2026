const LIVE = "https://luis-ticas1--keyframe-web.modal.run/";
const catalog = document.querySelector("#catalog"),
  launch = document.querySelector("#launch"),
  film = document.querySelector("#film"),
  intro = document.querySelector("#intro"),
  site = document.querySelector("#site"),
  info = document.querySelector("#info");
let endTimer;
function freshURL() {
  const u = new URL(LIVE);
  u.searchParams.set("launch", Date.now().toString());
  return u.href;
}
function playIntro() {
  clearTimeout(endTimer);
  intro.hidden = false;
  film.currentTime = 0;
  film.muted = true;
  document.querySelector("#sound").textContent = "Sound on";
  document.querySelector("#enter").textContent = "Enter Keyframe →";
  film.play().catch(() => {
    film.controls = true;
  });
}
function render() {
  clearTimeout(endTimer);
  stopSequence();
  const active = new URL(location.href).searchParams.get("view") === "game";
  catalog.hidden = active;
  launch.hidden = !active;
  if (active) {
    const url = freshURL();
    site.src = url;
    document.querySelector("#direct").href = url;
    playIntro();
  } else {
    film.pause();
    site.removeAttribute("src");
    startSequence();
  }
}
function openGame(e) {
  e?.preventDefault();
  if (info.open) info.close();
  const u = new URL(location.href);
  u.searchParams.set("view", "game");
  u.searchParams.set("fresh", Date.now().toString());
  history.pushState({}, "", u);
  render();
  window.scrollTo(0, 0);
}
function back() {
  const u = new URL(location.href);
  u.search = "";
  history.pushState({}, "", u);
  render();
}
function enter() {
  clearTimeout(endTimer);
  film.pause();
  intro.hidden = true;
}
document
  .querySelectorAll("[data-launch]")
  .forEach((a) => a.addEventListener("click", openGame));
document.querySelector("#back").onclick = back;
document.querySelector("#return").onclick = back;
document.querySelector("#enter").onclick = enter;
document.querySelector("#replay").onclick = playIntro;
document.querySelector("#sound").onclick = () => {
  film.muted = !film.muted;
  document.querySelector("#sound").textContent = film.muted
    ? "Sound on"
    : "Sound off";
};
film.onended = () => {
  document.querySelector("#enter").textContent = "Enter Keyframe →";
  endTimer = setTimeout(enter, 4000);
};
window.onpopstate = render;
function showInfo(title, copy, keyframe) {
  document.querySelector("#info-title").textContent = title;
  document.querySelector("#info-copy").textContent = copy;
  document.querySelector("#info-play").hidden = !keyframe;
  info.showModal();
}
document.querySelector("#more").onclick = () =>
  showInfo(
    "Keyframe",
    "Photograph a room and explore an escape game built around your own objects. Meet the Architect, Riddler, Guide and Trickster. Play Game opens the real Keyframe website with its original opening video replayed on every launch.",
    true,
  );
document.querySelector(".close").onclick = () => info.close();
info.addEventListener("click", (e) => {
  if (e.target === info) info.close();
});
document
  .querySelectorAll(".reference")
  .forEach(
    (b) =>
      (b.onclick = () =>
        showInfo(
          b.dataset.title,
          "This is reference artwork from the supplied Netflix screenshot. Keyframe is the playable featured game in this independent concept.",
          false,
        )),
  );
document.querySelector("#search").onclick = () => {
  document.querySelector("#games").scrollIntoView();
  document.querySelector(".keyframe-tile").focus();
};
const hero = document.querySelector(".hero"),
  conjuring = document.querySelector("#conjuringFirst"),
  tutorial = document.querySelector("#tutorialHero");
let heroTimers = [];
function stopSequence() {
  heroTimers.forEach(clearTimeout);
  heroTimers = [];
  tutorial.pause();
}
function showKeyframe() {
  stopSequence();
  conjuring.classList.add("fading");
  conjuring.setAttribute("aria-hidden", "true");
  conjuring.tabIndex = -1;
  heroTimers.push(
    setTimeout(() => {
      tutorial.currentTime = 0;
      tutorial
        .play()
        .then(() => hero.classList.add("motion"))
        .catch(() => {});
    }, 2900),
  );
}
function startSequence() {
  stopSequence();
  hero.classList.remove("motion");
  conjuring.classList.remove("fading");
  conjuring.removeAttribute("aria-hidden");
  conjuring.tabIndex = 0;
  tutorial.currentTime = 0;
  heroTimers.push(setTimeout(showKeyframe, 5000));
}
document.querySelector("#sequenceReplay").onclick = startSequence;
conjuring.onclick = showKeyframe;
document.addEventListener("keydown", (e) => {
  if (
    e.key.toLowerCase() === "r" &&
    !e.ctrlKey &&
    !e.metaKey &&
    !info.open &&
    !catalog.hidden
  )
    startSequence();
});
render();
