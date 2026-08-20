"""Models and findings in, HTML out. Pure: no I/O, no clock (beyond parsing
an already-supplied date string), no subprocess, no randomness.
"""

from __future__ import annotations

import html as _html
from datetime import datetime

from . import analyse

CSS = """
/* Aethyron / Aether design system.
   Light layer from Aether app.css; dark layer from Aethyron tokens.css.
   Webfonts are NOT imported — this page must stay self-contained and work
   offline on loopback. Aether's own stacks already name the fallbacks used
   here (Georgia for the editorial serif, Menlo for mono). */
.gf {
  color-scheme: light;
  --surface-1:#ffffff; --plane:#faf7f1; --sunken:#f4efe5;
  --ink-1:#0a1224; --ink-2:#4b5772; --ink-3:#6b7791;
  --grid:rgba(10,18,36,0.08); --baseline:rgba(10,18,36,0.14); --ring:rgba(10,18,36,0.08);
  --done:#1e3a8a; --wip:#3b82f6; --todo:#60a5fa;
  --good:#1f6f4a; --warning:#8a5a0d; --serious:#b3261e; --critical:#9c1f17;
  --on-status:#faf7f1;
  --badge-bg:#e3ebf9; --badge-fg:#1e3a8a;
  --shadow:0 1px 2px rgba(10,18,36,0.05);
  --font-display:'Source Serif 4','Tiempos Headline',Georgia,'Times New Roman',serif;
  --font-body:'Inter','Söhne',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;
  --font-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .gf {
    color-scheme: dark;
    --surface-1:#0a1224; --plane:#050b18; --sunken:#0f1a33;
    --ink-1:#f4efe5; --ink-2:#cdd3e0; --ink-3:#98a2b8;
    --grid:rgba(250,247,241,0.08); --baseline:rgba(250,247,241,0.16); --ring:rgba(250,247,241,0.10);
    --done:#93c5fd; --wip:#3b82f6; --todo:#2952c2;
    --good:#3d9668; --warning:#d9a441; --serious:#d4574c; --critical:#e06a60;
    --on-status:#050b18;
    --badge-bg:rgba(59,130,246,0.14); --badge-fg:#93c5fd;
    --shadow:none;
  }
}
:root[data-theme="dark"] .gf {
  color-scheme: dark;
  --surface-1:#0a1224; --plane:#050b18; --sunken:#0f1a33;
  --ink-1:#f4efe5; --ink-2:#cdd3e0; --ink-3:#98a2b8;
  --grid:rgba(250,247,241,0.08); --baseline:rgba(250,247,241,0.16); --ring:rgba(250,247,241,0.10);
  --done:#93c5fd; --wip:#3b82f6; --todo:#2952c2;
  --good:#3d9668; --warning:#d9a441; --serious:#d4574c; --critical:#e06a60;
  --on-status:#050b18;
  --badge-bg:rgba(59,130,246,0.14); --badge-fg:#93c5fd;
  --shadow:none;
}
.gf * { box-sizing: border-box; }
/* One rule for every element the client script hides, deliberately not one
   per element. `hide` is the only class FEED_JS toggles to remove something
   from the page, and a per-element rule has to be remembered each time the
   script learns to hide something new. It was not remembered for `.gf-tk`:
   the task chips toggled `hide` on rows that had no `.gf-tk.hide` rule, so
   clicking "blocked 3" darkened the chip and left all 52 rows on screen
   under a chip asserting only the blocked ones were shown. Everything the
   dashboard renders lives inside `.gf`, so this covers the next one too. */
.gf .hide { display:none; }
.gf-app { background: var(--plane); padding: 28px; border-radius: 4px; border: 1px solid var(--ring); overflow-x:auto; }
.gf-card { background: var(--surface-1); border: 1px solid var(--ring); border-radius: 4px; padding: 20px 22px; box-shadow: var(--shadow); }
/* Flex, because this heading carries two children: the card's name and,
   in the feed's case, a live count written by FEED_JS. As a plain block
   the two ran together and the page rendered "ACTIVITYNO PREVIOUS VISIT
   RECORDED" as one word. Space-between also puts the count on the right,
   which is where the eye looks for it. Headings with a single child are
   unaffected. */
/* Navigation renders only in portfolio mode, so it must not reserve space
   when absent — no min-height, no empty container. */
.gf-owner { font-family:var(--font-body); font-size:11px; color:var(--ink-2);
  margin-left:auto; padding-right:14px; white-space:nowrap; }
.gf-owner.none { color:var(--ink-3); font-style:italic; }
.gf-drift { margin-top:8px; }
.gf-drift > summary { font-size:11px; color:var(--ink-3); cursor:pointer; list-style:none; }
.gf-drift > summary::-webkit-details-marker { display:none; }
.gf-drift > summary::before { content:"\203A "; display:inline-block; transition:transform 120ms; }
.gf-drift[open] > summary::before { transform:rotate(90deg); }
.gf-drift > summary:hover { color:var(--ink-1); }
.gf-diff { margin-top:8px; border:1px solid var(--grid); border-radius:4px; overflow-x:auto; }
.gf-dl { font-family:var(--font-mono); font-size:10.5px; line-height:1.6; padding:1px 8px;
  white-space:pre; }
.gf-dl.add { color:var(--good); }
.gf-dl.del { color:var(--critical); }
.gf-dl.at { color:var(--ink-3); background:var(--sunken); }
.gf-dl.ctx { color:var(--ink-3); }
.gf-dwhy { font-style:italic; }
.gf-nav { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:18px;
  font-family:var(--font-body); font-size:11px; letter-spacing:.04em; }
/* The arrow is the literal character, not a CSS escape. `content:"\2190"`
   without a terminating space renders as the text "90" in some parsers, which
   is what shipped the first time. */
.gf-up { color:var(--ink-2); text-decoration:none; }
.gf-up:hover { color:var(--ink-1); text-decoration:underline; }
.gf-navsep { color:var(--ink-3); }
/* Same tokens as .gf-chip. Three variables invented for this block — --bg,
   --line and --accent — exist nowhere in the stylesheet; an undefined custom
   property falls back silently, so the active engagement rendered dark text on
   a dark background and nothing complained. */
.gf-eng { font-size:11px; color:var(--ink-2); text-decoration:none; padding:4px 10px;
  border-radius:11px; border:1px solid var(--grid); background:var(--surface-1); }
.gf-eng:hover { color:var(--ink-1); border-color:var(--ink-3); }
.gf-eng.on { background:var(--ink-1); color:var(--surface-1); border-color:var(--ink-1); }
.gf-h { display:flex; align-items:baseline; justify-content:space-between; gap:12px;
  font-size: 10.5px; letter-spacing: .18em; text-transform: uppercase; color: var(--ink-3); margin: 0 0 16px; font-weight: 500; }
.gf-top { display:flex; align-items:baseline; justify-content:space-between; margin-bottom:24px; gap:16px; flex-wrap:wrap; }
.gf-client { font-family:var(--font-display); font-size:30px; font-weight:380; letter-spacing:-.02em;
  line-height:1.1; color:var(--ink-1); }
.gf-meta { font-family:var(--font-mono); font-size:11px; color:var(--ink-3); letter-spacing:.01em; }
.gf-gates { display:flex; align-items:flex-start; }
.gf-gate { flex:1; position:relative; text-align:center; padding-top:26px; }
.gf-gate::before { content:""; position:absolute; top:9px; left:0; right:0; height:2px; background:var(--grid); }
.gf-gate:first-child::before { left:50%; }
.gf-gate:last-child::before { right:50%; }
.gf-gate.done::before { background:var(--good); }
.gf-dot { position:absolute; top:0; left:50%; transform:translateX(-50%); width:20px; height:20px; border-radius:50%;
  display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700;
  background:var(--grid); color:var(--ink-3); border:2px solid var(--surface-1); }
.gf-gate.done .gf-dot { background:var(--good); color:var(--on-status); }
.gf-gate.now  .gf-dot { background:var(--wip); color:var(--on-status); box-shadow:0 0 0 4px color-mix(in srgb, var(--wip) 20%, transparent); }
.gf-gate.bad  .gf-dot { background:var(--critical); color:var(--on-status); }
.gf-gname { font-family:var(--font-display); font-size:15px; font-weight:400; letter-spacing:-.01em; color:var(--ink-1); }
.gf-gsub { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); margin-top:5px; font-variant-numeric:tabular-nums; }
.gf-gate.todo .gf-gname { color:var(--ink-3); }
.gf-badge { display:inline-block; font-size:10px; font-weight:500; letter-spacing:.02em;
  padding:2px 8px; border-radius:4px; background:var(--badge-bg); color:var(--badge-fg); margin-top:5px; }
.gf-hero { font-family:var(--font-display); font-size:44px; font-weight:380; color:var(--ink-1); line-height:1;
  letter-spacing:-.02em; font-variant-numeric:tabular-nums; }
.gf-dropped { font-family:var(--font-mono); font-size:11px; font-weight:500; color:var(--ink-3);
  margin-left:12px; vertical-align:middle; letter-spacing:.01em; }
.gf-herosub { font-size:12.5px; color:var(--ink-2); margin-top:8px; }
.gf-bar { display:flex; gap:2px; height:12px; margin:16px 0 12px; }
.gf-seg { height:100%; }
.gf-seg:first-child { border-radius:2px 0 0 2px; }
.gf-seg:last-child { border-radius:0 2px 2px 0; }
.gf-key { display:flex; gap:16px; flex-wrap:wrap; }
.gf-kitem { display:flex; align-items:center; gap:6px; font-size:11.5px; color:var(--ink-2); }
.gf-sw { width:8px; height:8px; border-radius:2px; flex:none; }
.gf-kn { font-family:var(--font-mono); font-variant-numeric:tabular-nums; font-weight:500; color:var(--ink-1); }
.gf-tbl { width:100%; border-collapse:collapse; font-size:13px; }
.gf-tbl th { text-align:left; font-size:10.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-3);
  font-weight:500; padding:0 12px 10px 0; border-bottom:1px solid var(--grid); }
.gf-tbl td { padding:11px 12px 11px 0; border-bottom:1px solid var(--grid); color:var(--ink-2); vertical-align:middle; }
.gf-rid { font-family:var(--font-mono); font-variant-numeric:tabular-nums; font-weight:500; color:var(--ink-3); width:42px; font-size:11.5px; }
.gf-rtext { color:var(--ink-1); }
.gf-mini { display:flex; gap:2px; height:6px; width:104px; }
.gf-mini span:first-child { border-radius:2px 0 0 2px; }
.gf-mini span:last-child { border-radius:0 2px 2px 0; }
.gf-empty { height:6px; width:104px; border:1px dashed var(--critical); border-radius:2px; }
.gf-n { font-family:var(--font-mono); font-variant-numeric:tabular-nums; color:var(--ink-3); font-size:11px; width:52px; }
.gf-flag { display:inline-flex; align-items:center; gap:5px; font-size:11px; font-weight:500; }
.gf-flag.crit { color:var(--critical); }
.gf-flag.ok { color:var(--ink-3); }
.gf-att { display:flex; flex-direction:column; gap:0; }
.gf-item { display:flex; gap:10px; align-items:flex-start; padding:12px 0; border-top:1px solid var(--grid); }
/* Same reason as .gf-row > *: the text column holds the drift diff, whose
   pre-formatted lines are wider than the card. Without this the flex item
   refuses to shrink and the whole attention panel overflows the page. */
.gf-item > div:last-child { min-width:0; flex:1; }
.gf-item:first-child { border-top:0; padding-top:0; }
.gf-ico { flex:none; width:15px; height:15px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:9.5px; font-weight:700; color:var(--on-status); margin-top:2px; }
.gf-ico.crit { background:var(--critical); }
.gf-ico.ser  { background:var(--serious); }
.gf-ico.warn { background:var(--warning); }
.gf-itxt { font-size:12.5px; color:var(--ink-1); line-height:1.5; }
.gf-isub { font-size:11.5px; color:var(--ink-3); margin-top:3px; line-height:1.5; }
.gf-lbl { font-weight:600; }
/* min-width:0 on the tracks is load-bearing. A grid item defaults to
   min-width:auto and will not shrink below its content, so one wide
   white-space:pre line inside the diff pushed the right column out and
   squeezed the activity feed into a vertical ribbon. With this, the diff's
   own overflow-x:auto does the scrolling instead. */
.gf-row { display:grid; grid-template-columns: 1.65fr 1fr; gap:16px; margin-top:16px; }
.gf-row > * { min-width:0; }
.gf-split { display:grid; grid-template-columns: 160px 1fr; gap:28px; align-items:start; }
.gf-foot { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); margin-top:10px; letter-spacing:.01em; }
.gf-none { font-size:13px; color:var(--ink-3); margin:0; }
.gf-bad  { font-size:13px; color:var(--critical); margin:0; font-weight:500; }
.gf-stale{ font-family:var(--font-mono); font-size:11px; color:var(--ink-3); }

/* ---- masthead ------------------------------------------------ */
.gf-mast { display:flex; justify-content:space-between; align-items:flex-start; gap:24px;
  padding-bottom:28px; margin-bottom:28px; border-bottom:1px solid var(--baseline); flex-wrap:wrap; }
.gf-eyebrow { font-size:10.5px; letter-spacing:.18em; text-transform:uppercase; color:var(--ink-3);
  font-weight:500; }
.gf-title { font-family:var(--font-display); font-size:clamp(34px,4.4vw,52px); font-weight:380;
  letter-spacing:-.025em; line-height:1.02; color:var(--ink-1); margin:12px 0 0; }
.gf-shape { font-family:var(--font-display); font-style:italic; font-size:19px; color:var(--ink-3);
  margin-top:8px; display:block; }
.gf-tags { display:flex; gap:8px; margin-top:16px; flex-wrap:wrap; align-items:center; }
.gf-tag { font-family:var(--font-mono); font-size:10.5px; padding:4px 9px; border-radius:4px;
  background:var(--sunken); color:var(--ink-2); letter-spacing:.02em; }
.gf-toggle { display:flex; gap:0; border:1px solid var(--ring); border-radius:4px; overflow:hidden; flex:none; }
.gf-toggle button { font-family:var(--font-body); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
  padding:6px 11px; background:transparent; color:var(--ink-3); border:0; cursor:pointer;
  transition:background 140ms cubic-bezier(.2,.6,.2,1), color 140ms cubic-bezier(.2,.6,.2,1); }
.gf-toggle button + button { border-left:1px solid var(--ring); }
.gf-toggle button:hover { background:var(--sunken); color:var(--ink-1); }
.gf-toggle button[aria-pressed="true"] { background:var(--ink-1); color:var(--surface-1); }
.gf-toggle button:focus-visible { outline:2px solid var(--wip); outline-offset:-2px; }

/* ---- the spine (signature element) --------------------------- */
.gf-spine { display:grid; grid-auto-flow:column; grid-auto-columns:1fr; margin:0 0 30px; }
.gf-stn { position:relative; padding:34px 14px 0 0; }
.gf-stn::before { content:""; position:absolute; top:11px; left:0; right:0; height:1px; background:var(--grid); }
.gf-stn.done::before { background:var(--good); }
.gf-stn.bad::before  { background:var(--critical); }
.gf-stn:last-child::before { right:auto; width:22px; }
.gf-num { position:absolute; top:0; left:0; width:22px; height:22px; border-radius:50%;
  display:flex; align-items:center; justify-content:center; font-family:var(--font-mono); font-size:10px;
  font-weight:500; background:var(--surface-1); color:var(--ink-3); border:1px solid var(--grid); }
.gf-stn.done .gf-num { background:var(--good); color:var(--on-status); border-color:var(--good); }
.gf-stn.now  .gf-num { background:var(--wip); color:var(--on-status); border-color:var(--wip);
  box-shadow:0 0 0 4px color-mix(in srgb, var(--wip) 18%, transparent); }
.gf-stn.bad  .gf-num { background:var(--critical); color:var(--on-status); border-color:var(--critical); }
.gf-sname { font-family:var(--font-display); font-size:17px; font-weight:400; letter-spacing:-.01em;
  color:var(--ink-1); line-height:1.2; }
.gf-stn.todo .gf-sname { color:var(--ink-3); }
.gf-sev { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); margin-top:6px; line-height:1.6;
  letter-spacing:.01em; }
.gf-sev b { display:block; font-weight:500; color:var(--ink-2); }
.gf-stn.bad .gf-sev { color:var(--critical); }

/* ---- gate rail (side column, feed-led layout) ----------------- */
.gf-rail { display:flex; flex-direction:column; margin-bottom:16px; }
.gf-rs { display:flex; align-items:flex-start; gap:10px; padding:10px 0; border-top:1px solid var(--grid); }
.gf-rs:first-child { border-top:0; padding-top:0; }
.gf-rs .gf-num { position:static; flex:none; width:20px; height:20px; border-radius:50%;
  display:flex; align-items:center; justify-content:center; font-family:var(--font-mono);
  font-size:9.5px; font-weight:500; background:var(--surface-1); color:var(--ink-3);
  border:1px solid var(--grid); }
.gf-rs.done .gf-num { background:var(--good); color:var(--on-status); border-color:var(--good); }
.gf-rs.now  .gf-num { background:var(--wip); color:var(--on-status); border-color:var(--wip); }
.gf-rs.bad  .gf-num { background:var(--critical); color:var(--on-status); border-color:var(--critical); }
.gf-rn { font-family:var(--font-display); font-size:13.5px; font-weight:400; letter-spacing:-.01em;
  color:var(--ink-1); line-height:1.3; }
.gf-rs.todo .gf-rn { color:var(--ink-3); }
.gf-rsub { font-family:var(--font-mono); font-size:9.5px; color:var(--ink-3); margin-top:3px; line-height:1.4; }
.gf-rs.bad .gf-rsub { color:var(--critical); }
.gf-railstats { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--ring);
  border:1px solid var(--ring); border-radius:4px; overflow:hidden; }
.gf-railstats .gf-stat { padding:14px 16px; }
.gf-railstats .gf-sval { font-size:22px; }

/* ---- stat row ------------------------------------------------ */
.gf-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:1px; background:var(--ring);
  border:1px solid var(--ring); border-radius:4px; overflow:hidden; margin-bottom:16px; }
.gf-stat { background:var(--surface-1); padding:16px 18px; }
.gf-slabel { font-size:10px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3); font-weight:500; }
.gf-sval { font-family:var(--font-display); font-size:30px; font-weight:380; letter-spacing:-.02em;
  color:var(--ink-1); margin-top:8px; line-height:1; font-variant-numeric:tabular-nums; }
.gf-sval.muted { color:var(--ink-3); }
.gf-ssub { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); margin-top:7px; letter-spacing:.01em; }

/* ---- editorial narrative ------------------------------------- */
.gf-narr { font-family:var(--font-display); font-size:21px; font-weight:380; line-height:1.45;
  color:var(--ink-1); letter-spacing:-.005em; margin:14px 0 0; }
.gf-narr em { font-style:italic; }
.gf-secthead { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; margin-bottom:14px; }
.gf-secttitle { font-family:var(--font-display); font-size:22px; font-weight:400; letter-spacing:-.015em;
  color:var(--ink-1); margin:6px 0 0; }

/* ---- portfolio index ----------------------------------------- */
.gf-elist { display:flex; flex-direction:column; }
.gf-erow { display:grid; grid-template-columns:1.6fr 1fr 0.6fr 0.9fr; gap:18px; align-items:center;
  padding:18px 6px; border-top:1px solid var(--grid); text-decoration:none; color:inherit;
  transition:background 140ms cubic-bezier(.2,.6,.2,1); }
.gf-erow:first-child { border-top:0; }
.gf-erow:hover { background:var(--sunken); }
.gf-erow:focus-visible { outline:2px solid var(--wip); outline-offset:-2px; }
.gf-ename { font-family:var(--font-display); font-size:20px; font-weight:400; letter-spacing:-.015em;
  color:var(--ink-1); line-height:1.2; }
.gf-ename.muted { color:var(--ink-3); }
.gf-eslug { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); margin-top:4px; letter-spacing:.01em; }
.gf-emeta { font-size:12.5px; color:var(--ink-2); }
.gf-emono { font-family:var(--font-mono); font-size:12.5px; color:var(--ink-2); font-variant-numeric:tabular-nums; }
.gf-edot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; vertical-align:middle; }

@media (max-width: 820px) {
  .gf-erow { grid-template-columns:1fr 1fr; row-gap:8px; }
}
@media (max-width: 820px) {
  .gf-row, .gf-split { grid-template-columns:1fr; }
  .gf-stats { grid-template-columns:repeat(2,1fr); }
  .gf-spine { grid-auto-flow:row; grid-auto-columns:auto; }
  .gf-stn::before { display:none; }
}
@media (prefers-reduced-motion: reduce) {
  .gf * { transition:none !important; }
}

/* ---- activity feed ------------------------------------------- */
.gf-feed { display:flex; flex-direction:column; }
.gf-ev { display:grid; grid-template-columns:58px 18px 1fr auto; gap:11px; align-items:baseline;
  padding:11px 0; border-top:1px solid var(--grid); }
.gf-ev:first-child { border-top:0; }
.gf-ev .gf-when { font-family:var(--font-mono); font-size:10.5px; color:var(--ink-3); }
.gf-ev .gf-tdot { width:7px; height:7px; border-radius:50%; justify-self:center; align-self:center; }
.gf-ev .gf-etxt { font-size:13px; color:var(--ink-1); line-height:1.45; }
.gf-ev .gf-esha { font-family:var(--font-mono); font-size:10px; color:var(--ink-3); }
.gf-ev.gf-new { background:linear-gradient(90deg,color-mix(in srgb,var(--wip) 8%,transparent),transparent 65%);
  margin:0 -10px; padding-left:10px; padding-right:10px; }
.gf-newmark { font-family:var(--font-mono); font-size:9px; letter-spacing:.1em; text-transform:uppercase; color:var(--wip); }
.gf-fdiv { display:flex; align-items:center; gap:10px; padding:15px 0 7px; font-family:var(--font-mono);
  font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-3); }
.gf-fdiv::after { content:""; flex:1; height:1px; background:var(--grid); }
.gf-tbl details { border-top:1px solid var(--grid); }
.gf-tbl details:first-of-type { border-top:0; }
.gf-sum { display:grid; grid-template-columns:44px 1fr 110px 66px; gap:12px; align-items:center;
  padding:12px 0; cursor:pointer; list-style:none; }
.gf-sum::-webkit-details-marker { display:none; }
.gf-sum:hover { background:var(--sunken); }
.gf-sum:focus-visible { outline:2px solid var(--wip); outline-offset:-2px; }
.gf-exp { padding:2px 0 18px 56px; }
.gf-clab { font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3);
  display:block; margin-bottom:5px; }
.gf-acc { font-family:var(--font-display); font-size:15.5px; color:var(--ink-1); line-height:1.5;
  margin-bottom:14px; }
.gf-tk { display:flex; gap:9px; align-items:center; font-size:12.5px; padding:7px 0;
  border-top:1px solid var(--grid); color:var(--ink-1); }
.gf-tk .gf-tid { font-family:var(--font-mono); font-size:11px; color:var(--ink-3); width:36px; }
.gf-tk .gf-item { font-family:var(--font-mono); font-size:10.5px; color:var(--wip); margin-left:auto; }
.gf-pill { font-size:9.5px; padding:2px 7px; border-radius:3px; background:var(--sunken);
  color:var(--ink-2); font-family:var(--font-mono); }
.gf-flagwrap { display:flex; flex-direction:column; align-items:flex-end; gap:2px; }

/* ---- filter chips -------------------------------------------- */
.gf-chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px; }
.gf-chip { font-family:var(--font-body); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; padding:5px 11px; border:1px solid var(--ring);
  border-radius:4px; color:var(--ink-3); background:transparent; cursor:pointer;
  transition:background 140ms cubic-bezier(.2,.6,.2,1),
             color 140ms cubic-bezier(.2,.6,.2,1); }
.gf-chip:hover { background:var(--sunken); color:var(--ink-1); }
.gf-chip.on { background:var(--ink-1); color:var(--surface-1); border-color:var(--ink-1); }
.gf-chip:focus-visible { outline:2px solid var(--wip); outline-offset:2px; }
"""


def _esc(value) -> str:
    return _html.escape(str(value), quote=True)


def _card(title: str, inner: str) -> str:
    return f'<div class="gf-card"><div class="gf-h">{_esc(title)}</div>{inner}</div>'


def _client(state) -> str:
    engagement = state.engagement.engagement
    return engagement.client if engagement else ""


def _phase(state) -> str:
    """One plain-language line for where the engagement stands. Derived only
    from gate state — never asserts anything the gates do not already say."""
    current = next((g for g in state.gates if g.state == "current"), None)
    # Both states mean the same thing at this level of summary: an approval on
    # record that no longer holds. They print differently in the rail, where
    # there is room to say WHY, but the headline must surface either one — when
    # this checked only "unverifiable", splitting the states out left the top
    # line reading "Build in progress" while a signed gate had drifted.
    unverified = [g for g in state.gates if g.state in ("changed", "unverifiable")]
    if unverified:
        names = ", ".join(g.name for g in unverified)
        return f"{names} sign-off needs re-checking"
    if current:
        return f"{current.name} in progress"
    approved = [g for g in state.gates if g.state == "approved"]
    if approved:
        return f"{approved[-1].name} approved"
    return "Not yet started"


_THEMES = (("auto", "Auto"), ("light", "Light"), ("dark", "Dark"))


def _toggle() -> str:
    buttons = "".join(
        f'<button type="button" data-set-theme="{key}" aria-pressed="false">{label}</button>'
        for key, label in _THEMES
    )
    return f'<div class="gf-toggle" role="group" aria-label="Colour theme">{buttons}</div>'


def _topbar(state) -> str:
    engagement = state.engagement.engagement
    tags = []
    if engagement:
        for value in (engagement.tracker_type, engagement.project, engagement.epic):
            if value:
                tags.append(value)
        if engagement.narrative:
            tags.append(engagement.narrative)
    tag_chips = "".join(f'<span class="gf-tag">{_esc(t)}</span>' for t in tags)
    tag_chips += '<span class="gf-tag">read-only</span>'

    # The page opens feed-led, so the range that governs "what moved" belongs
    # at the top, beside who/where this is — not buried in the feed card
    # below. These buttons share [data-range] with the feed's own toggle;
    # FEED_JS's click handler and its `markOn` both walk every element with
    # that attribute, so the two stay in sync automatically.
    #
    # No chip is marked `on` server-side. `on` means "this filter is what you
    # are looking at", and the server renders every row unfiltered — it cannot
    # know what "since your last visit" means for this browser. With JS
    # disabled, blocked, or throwing before `start()`, an `on` chip rendered
    # here would sit above the engagement's whole history asserting a filter
    # that was never applied. `markOn` establishes it once the script has
    # actually applied one.
    range_chips = (
        '<div class="gf-chips" role="group" aria-label="Time range">'
        '<button type="button" class="gf-chip" data-range="visit">Since last visit</button>'
        '<button type="button" class="gf-chip" data-range="7">7 days</button>'
        '<button type="button" class="gf-chip" data-range="all">All</button>'
        "</div>"
    )

    phase = _phase(state)
    if state.days_in_gate is not None:
        phase += f" · {state.days_in_gate} days in gate"

    return (
        '<header class="gf-mast"><div>'
        '<div class="gf-eyebrow">Engagement</div>'
        f'<h1 class="gf-title">{_esc(_client(state))}</h1>'
        f'<span class="gf-shape">{_esc(phase)}</span>'
        f'<div class="gf-tags">{tag_chips}</div>'
        f"{range_chips}"
        "</div>"
        f"{_toggle()}"
        "</header>"
    )


_GATE_CSS = {
    "approved": ("done", "✓"),
    "current": ("now", ""),
    "pending": ("todo", ""),
    "changed": ("bad", "!"),
    "unverifiable": ("bad", "?"),
}


def _gates(state) -> str:
    """The spine. Each gate is a numbered station carrying its own evidence:
    an approved gate shows the date it was signed and the commit it was signed
    at, set in mono beneath the name like a footnote on a record. A gate whose
    evidence cannot be checked says so in place of that footnote, and never
    shows the tick."""
    stations = []
    for index, gate in enumerate(state.gates):
        css, glyph = _GATE_CSS[gate.state]
        mark = glyph or str(index)
        if gate.state == "approved":
            evidence = f"<b>{_esc(gate.date)}</b>{_esc(gate.commit[:7])}"
        elif gate.state == "changed":
            evidence = (
                f"{_esc(gate.artifact)} changed since {_esc(gate.commit[:7])}"
                " — the approval no longer covers it"
            )
        elif gate.state == "unverifiable":
            evidence = (
                f"cannot verify: commit {_esc(gate.commit[:7])} is not in this repository"
            )
        elif gate.state == "current":
            evidence = '<span class="gf-badge">in progress</span>'
        else:
            evidence = "&mdash;"
        stations.append(
            f'<div class="gf-stn {css}">'
            f'<div class="gf-num" title="{_esc(gate.commit)}">{mark}</div>'
            f'<div class="gf-sname">{_esc(gate.name)}</div>'
            f'<div class="gf-sev">{evidence}</div>'
            "</div>"
        )
    return f'<div class="gf-spine">{"".join(stations)}</div>'


def _gates_legacy(state) -> str:
    cells = []
    for index, gate in enumerate(state.gates):
        css, glyph = _GATE_CSS[gate.state]
        dot = glyph or str(index)
        if gate.state == "approved":
            sub = f"{_esc(gate.date)} · {_esc(gate.commit[:7])}"
        elif gate.state == "changed":
            sub = (f"{_esc(gate.artifact)} changed since {_esc(gate.commit[:7])}"
                   " — the approval no longer covers it")
        elif gate.state == "unverifiable":
            sub = f"cannot verify: commit {_esc(gate.commit[:7])} is not in this repository"
        elif gate.state == "current":
            sub = '<span class="gf-badge">in progress</span>'
        else:
            sub = "—"
        cells.append(
            f'<div class="gf-gate {css}"><div class="gf-dot" title="{_esc(gate.commit)}">{dot}</div>'
            f'<div class="gf-gname">{_esc(gate.name)}</div>'
            f'<div class="gf-gsub">{sub}</div></div>'
        )
    return _card("Gates", f'<div class="gf-gates">{"".join(cells)}</div>')


_SEGMENTS = (
    ("done", "var(--done)", "Done"),
    ("in_progress", "var(--wip)", "In progress"),
    ("blocked", "var(--serious)", "Blocked"),
    ("todo", "var(--todo)", "Not started"),
)


def _bar(counts) -> str:
    segs, keys = [], []
    for attr, colour, label in _SEGMENTS:
        value = getattr(counts, attr)
        if value:
            segs.append(f'<div class="gf-seg" style="flex:{value};background:{colour}"></div>')
        keys.append(
            f'<div class="gf-kitem"><span class="gf-sw" style="background:{colour}"></span>'
            f'{label} <span class="gf-kn">{value}</span></div>'
        )
    return (
        f'<div class="gf-bar">{"".join(segs)}</div>'
        f'<div class="gf-key">{"".join(keys)}</div>'
    )


def _short_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b").lstrip("0")
    except (ValueError, TypeError):
        return iso[:10]


_TONE_COLOUR = {
    "milestone": "var(--good)",
    "scope": "var(--critical)",
    "attention": "var(--serious)",
    "progress": "var(--wip)",
}


def _feed(state) -> str:
    feed = state.feed
    if not feed.history_ok:
        return _card("Activity", '<p class="gf-none">No history available — the feed needs git.</p>')
    if not feed.events and not feed.scanned:
        return _card("Activity", '<p class="gf-none">No engagement history yet.</p>')

    rows = []
    for event in feed.events:
        colour = _TONE_COLOUR.get(event.tone, "var(--ink-3)")
        rows.append(
            f'<div class="gf-ev" data-when="{_esc(event.when)}" data-commit="{_esc(event.commit)}" '
            f'data-kind="{_esc(event.kind)}">'
            f'<span class="gf-when">{_esc(_short_date(event.when))}</span>'
            f'<span class="gf-tdot" style="background:{colour}"></span>'
            f'<span class="gf-etxt">{_esc(event.text)}</span>'
            f'<span class="gf-esha">{_esc(event.commit[:7])}</span>'
            "</div>"
        )

    # A brand-new engagement has exactly one commit, so "1 commits scanned" is
    # the first sentence many people read from this product.
    note = f"{feed.scanned} commit{'' if feed.scanned == 1 else 's'} scanned"
    if feed.unreadable:
        note += (f" · {feed.unreadable} could not be read, so events may be missing")
    if feed.truncated:
        note += (
            f" · showing {len(feed.events)} most recent of "
            f"{len(feed.events) + feed.truncated}"
        )

    # The divider is emitted once, hidden. The server cannot know which rows
    # are new — only the client can — so the client moves it after the last
    # new row and unhides it. Rendering it server-side would require the server
    # to know who is looking, which is exactly what this design avoids.
    divider = '<div class="gf-fdiv hide" id="gf-earlier">earlier</div>'
    heading = (
        '<span>Activity</span>'
        '<span class="note" id="gf-feedcount"></span>'
    )
    # No range toggle here. `_topbar` owns it — the layout rework moved the
    # chips up beside who and where the engagement is, and this copy was left
    # behind. The page therefore served SIX [data-range] buttons in two groups
    # both labelled "Time range", in different orders (visit/7/all above,
    # 7/all/visit here), and because FEED_JS walks every element carrying the
    # attribute, clicking either lit both. `_feed` is only ever rendered
    # beside `_topbar` (see `body`), so the handler still has buttons to bind.
    body = (
        f'<div class="gf-feed" id="gf-feed">{divider}{"".join(rows)}</div>'
        + f'<div class="gf-foot">{_esc(note)}</div>'
    )
    return (
        f'<div class="gf-card"><div class="gf-h">{heading}</div>{body}</div>'
    )


def _trend(state) -> str:
    if not state.is_repo:
        return '<p class="gf-none">No git history available.</p>'
    if not state.trend.history_ok:
        # git itself could not be read (corrupt object store, permissions,
        # timeout) — distinct from "read git fine, tasks.md has no history
        # yet" below. Asserting the latter here would be a false positive.
        return '<p class="gf-bad">Cannot read history for tasks.md.</p>'
    if not state.trend.points:
        return '<p class="gf-none">No committed history for tasks.md yet.</p>'

    readable = [(i, p) for i, p in enumerate(state.trend.points)
                if p.readable and p.remaining is not None]
    if not readable:
        return (
            '<p class="gf-bad">'
            f'{len(state.trend.points)} revisions of tasks.md, none readable.'
            '</p>'
        )

    points = state.trend.points
    n = len(points)

    def x(i: int) -> float:
        return 30 + i * 370 / max(n - 1, 1)

    peak = max((p.remaining for _, p in readable), default=1) or 1

    def y(v: int) -> float:
        return 108 - (v / peak) * 98

    runs: list[list[int]] = []
    current: list[int] = []
    for i, p in enumerate(points):
        if p.readable and p.remaining is not None:
            current.append(i)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)

    parts = []

    # 1. Gridlines + y labels
    parts.append(f'<line x1="30" y1="10" x2="400" y2="10" stroke="var(--grid)" stroke-width="1"/>')
    parts.append(f'<line x1="30" y1="59" x2="400" y2="59" stroke="var(--grid)" stroke-width="1"/>')
    parts.append(f'<line x1="30" y1="108" x2="400" y2="108" stroke="var(--baseline)" stroke-width="1"/>')
    parts.append(f'<text x="24" y="14" text-anchor="end" font-size="9.5" fill="var(--ink-3)">{_esc(peak)}</text>')
    # The gridline itself sits at y(peak / 2) (== pixel 59 for any peak, by
    # construction). The label must name that same value — `peak // 2` named
    # a different number from the line it labelled whenever peak was odd.
    mid_value = peak / 2
    mid_label = f"{mid_value:g}"
    parts.append(f'<text x="24" y="62" text-anchor="end" font-size="9.5" fill="var(--ink-3)">{_esc(mid_label)}</text>')
    parts.append('<text x="24" y="111" text-anchor="end" font-size="9.5" fill="var(--ink-3)">0</text>')

    # 2. Area fill, per solid run only (length >= 2)
    for run in runs:
        if len(run) < 2:
            continue
        coords = [(x(i), y(points[i].remaining)) for i in run]
        path = f"M{coords[0][0]},{coords[0][1]} " + " ".join(
            f"L{px},{py}" for px, py in coords[1:]
        )
        last_x = coords[-1][0]
        first_x = coords[0][0]
        path += f" L{last_x},108 L{first_x},108 Z"
        parts.append(f'<path d="{path}" fill="var(--wip)" opacity="0.13"/>')

    # 3. Solid polylines, per run
    for run in runs:
        if len(run) < 2:
            continue
        pts = " ".join(f"{x(i)},{y(points[i].remaining)}" for i in run)
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="var(--wip)" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )

    def _gap_marker(gx: float, gy: float) -> None:
        parts.append(
            f'<circle cx="{gx}" cy="{gy}" r="4.5" fill="var(--surface-1)" '
            f'stroke="var(--ink-3)" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{gx}" y="{gy - 13}" text-anchor="middle" font-size="9" '
            f'fill="var(--ink-3)">unreadable</text>'
        )

    # 4. Leading gap: unreadable points before the first readable run. There
    # is no earlier data point to bridge from, so the marker sits at the
    # first readable value rather than inventing a line back to x(0) — the
    # expected state on adoption, since every revision predating this
    # branch's tasks.md format will fail to parse.
    first_run_start = runs[0][0]
    if first_run_start > 0:
        anchor_y = y(points[first_run_start].remaining)
        for gap_i in range(0, first_run_start):
            _gap_marker(x(gap_i), anchor_y)

    # 5. Dashed bridges across gaps between two readable runs + gap markers
    for run_index in range(len(runs) - 1):
        end_i = runs[run_index][-1]
        start_i = runs[run_index + 1][0]
        x1, y1 = x(end_i), y(points[end_i].remaining)
        x2, y2 = x(start_i), y(points[start_i].remaining)
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="var(--ink-3)" '
            f'stroke-width="2" stroke-dasharray="3 3"/>'
        )
        mid_y = (y1 + y2) / 2
        for gap_i in range(end_i + 1, start_i):
            _gap_marker(x(gap_i), mid_y)

    # 6. Trailing gap: unreadable points after the last readable run.
    last_run_end = runs[-1][-1]
    if last_run_end < n - 1:
        anchor_y = y(points[last_run_end].remaining)
        for gap_i in range(last_run_end + 1, n):
            _gap_marker(x(gap_i), anchor_y)

    # 7. Final readable point
    last_i, last_p = readable[-1]
    lx, ly = x(last_i), y(last_p.remaining)
    parts.append(
        f'<circle cx="{lx}" cy="{ly}" r="4.5" fill="var(--wip)" stroke="var(--surface-1)" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{lx - 6}" y="{ly + 16}" text-anchor="end" font-size="11" font-weight="700" '
        f'fill="var(--ink-1)">{_esc(last_p.remaining)} left</text>'
    )

    # 8. X axis labels
    first_i, first_p = readable[0]
    parts.append(
        f'<text x="{x(first_i)}" y="124" font-size="9.5" fill="var(--ink-3)">'
        f'{_esc(_short_date(first_p.date))}</text>'
    )
    parts.append(
        f'<text x="{x(last_i)}" y="124" text-anchor="end" font-size="9.5" fill="var(--ink-3)">'
        f'{_esc(_short_date(last_p.date))}</text>'
    )

    aria = (
        f"Tasks remaining fell from {first_p.remaining} on {_short_date(first_p.date)} "
        f"to {last_p.remaining} on {_short_date(last_p.date)}"
    )
    if state.trend.unreadable:
        aria += f", with {state.trend.unreadable} unreadable revision(s) plotted as a gap"

    svg = (
        '<svg viewBox="0 0 440 130" width="100%" style="display:block;max-width:460px" '
        f'role="img" aria-label="{_esc(aria)}">' + "".join(parts) + "</svg>"
    )

    # Totals at each end ("52 → 18"), plus the current dropped count when
    # non-zero ("2 dropped") — a scope cut lowers the line exactly as
    # completing work does, so it must not be mistaken for delivery.
    dropped_count = analyse.count(state.tasks.tasks).dropped
    totals = f"{first_p.remaining} → {last_p.remaining}"
    if dropped_count:
        totals += f", {dropped_count} dropped"

    footnote = (
        totals
        + f" · {state.trend.readable + state.trend.unreadable} commits to tasks.md"
        + (
            f" · {state.trend.unreadable} revision"
            f"{'s' if state.trend.unreadable != 1 else ''} could not be parsed, plotted as a gap"
            if state.trend.unreadable
            else ""
        )
    )
    return svg + f'<div class="gf-foot">{_esc(footnote)}</div>'


def _tasks_panel(state) -> str:
    if not state.tasks.present:
        return _card("Tasks", '<p class="gf-none">No tasks yet — produced at gate 2.</p>')
    if not state.tasks.header_ok:
        # `p.message` already starts with "header not recognised — …" (see
        # parse.py); prefixing the same phrase again here would say it twice.
        detail = "; ".join(_esc(p.message) for p in state.tasks.problems)
        return _card("Tasks", f'<p class="gf-bad">tasks.md: {detail}</p>')
    if not state.tasks.tasks:
        return _card("Tasks", '<p class="gf-none">No tasks yet.</p>')

    counts = analyse.count(state.tasks.tasks)
    # `dropped` is excluded from the denominator above (see Counts.total_active),
    # so it must be shown explicitly beside the hero figure — otherwise a scope
    # cut silently raises the completion ratio with nothing on screen saying why.
    dropped = (
        f'<span class="gf-dropped">{_esc(counts.dropped)} dropped</span>'
        if counts.dropped
        else ""
    )
    hero = (
        f'<div class="gf-hero">{_esc(counts.done)}'
        f'<span style="font-size:20px;color:var(--ink-3);font-weight:500"> / {_esc(counts.total_active)}</span>'
        f"{dropped}</div>"
        f'<div class="gf-herosub">complete · {_esc(counts.in_progress)} in progress</div>'
    )
    left = hero + _bar(counts)
    right = (
        '<div style="font-size:11.5px;color:var(--ink-2);margin-bottom:2px;font-weight:600">'
        "Tasks remaining</div>" + _trend(state)
    )
    inner = (
        f'<div class="gf-split"><div>{left}</div><div>{right}</div></div>'
        + _task_rows(state.tasks.tasks)
    )
    return _card("Tasks", inner)


_STATUS_ORDER = ("done", "in-progress", "blocked", "todo", "dropped")


def _chip_labels(tasks):
    """('all', 'All 52') first, then one chip per status actually present, in
    a fixed order. Statuses with no tasks are omitted rather than shown as
    zero — an always-present 'Blocked 0' trains the eye to skip the row that
    matters most when it is not zero."""
    counts = {}
    for task in tasks:
        counts[task.status] = counts.get(task.status, 0) + 1
    labels = [("all", f"All {len(tasks)}")]
    for status in _STATUS_ORDER:
        if counts.get(status):
            labels.append((status, f"{status} {counts[status]}"))
    return tuple(labels)


def _task_rows(tasks) -> str:
    rows = "".join(
        f'<div class="gf-tk" data-status="{_esc(t.status)}" data-owner="{_esc(t.owner)}">'
        f'<span class="gf-tid">{_esc(t.id)}</span>{_esc(t.title)}'
        f'<span class="gf-pill">{_esc(t.status)}</span>'
        # Unassigned is shown greyed rather than hidden. On a team an
        # in-progress task with nobody on it is the thing worth noticing, and
        # an empty cell would read as "not filled in".
        f'<span class="gf-owner{"" if t.owner != "(unassigned)" else " none"}">'
        f'{_esc(t.owner)}</span>'
        f'<span class="gf-item">{_esc(t.item)}</span></div>'
        for t in tasks
    )
    chips = "".join(
        f'<button type="button" class="gf-chip" data-filter="{_esc(key)}">'
        f"{_esc(label)}</button>"
        for key, label in _chip_labels(tasks)
    )
    return (
        f'<div class="gf-chips">{chips}</div>'
        f'<div id="gf-tasklist">{rows}</div>'
        '<p class="gf-none gf-nomatch" hidden>No tasks with that status.</p>'
    )


def _coverage(state) -> str:
    if not state.reqs.present:
        return _card("Requirement coverage", '<p class="gf-none">No requirements.md yet — produced at gate 1.</p>')
    if not state.tasks.present:
        # Distinct from "checked and found none" (the ✕ no tasks flag below):
        # tasks.md has not been produced yet, so there is nothing to check.
        return _card(
            "Requirement coverage",
            '<p class="gf-none">Coverage not available yet — tasks.md is produced at gate 2.</p>',
        )
    if not state.tasks.header_ok:
        # tasks.md exists but the parser refused to read it. Coverage must
        # not be computed from an empty task list here — that would draw a
        # confident "✕ no tasks" for every requirement from a file we could
        # not actually read.
        return _card(
            "Requirement coverage",
            '<p class="gf-bad">Coverage cannot be computed — tasks.md unreadable.</p>',
        )
    if not state.tasks.tasks and not analyse.tasks_expected(state.signoffs):
        # The file exists and parses, but gate 2 has not run, so it is
        # legitimately empty. Flagging every requirement as uncovered here
        # would be a false alarm on every engagement before design sign-off.
        return _card(
            "Requirement coverage",
            '<p class="gf-none">Coverage not available yet — tasks.md is produced '
            "at gate 2, once design is signed off.</p>",
        )
    rows = []
    for row in analyse.coverage(state.reqs, state.tasks):
        if row.tasks:
            bars = "".join(
                f'<span style="flex:{getattr(row.counts, attr)};background:{colour}"></span>'
                for attr, colour, _ in _SEGMENTS
                if getattr(row.counts, attr)
            )
            tip_text = "; ".join(f"{t.id}: {t.title}" for t in row.tasks)
            tip = _esc(tip_text)
            cell = (
                f'<div class="gf-mini" role="img" aria-label="{tip}" title="{tip}">{bars}</div>'
            )
            flag = '<span class="gf-flag ok">covered</span>'
            count_text = f"{row.counts.done} / {row.counts.total_active}"
        else:
            cell = '<div class="gf-empty"></div>'
            flag = '<span class="gf-flag crit">✕ no tasks</span>'
            count_text = "0"
        summary = (
            '<summary class="gf-sum">'
            f'<span class="gf-rid">{_esc(row.requirement.id)}</span>'
            f'<span class="gf-rtext">{_esc(row.requirement.text)}</span>'
            f"{cell}"
            f'<span class="gf-flagwrap"><span class="gf-n">{_esc(count_text)}</span>{flag}</span>'
            "</summary>"
        )
        rows.append(f"<details>{summary}{_expansion(row)}</details>")
    head = "<tr><th>#</th><th>Requirement</th><th>Tasks</th><th></th><th></th></tr>"
    return _card("Requirement coverage", f'<table class="gf-tbl">{head}{"".join(rows)}</table>')


def _expansion(row) -> str:
    if row.requirement.criterion:
        criterion = (
            '<span class="gf-clab">Acceptance criterion</span>'
            f'<div class="gf-acc">{_esc(row.requirement.criterion)}</div>'
        )
    else:
        criterion = (
            '<span class="gf-clab">Acceptance criterion</span>'
            '<div class="gf-acc gf-none">No acceptance criterion recorded in '
            "requirements.md.</div>"
        )
    if not row.tasks:
        tasks = '<div class="gf-bad">No tasks trace to this requirement — unplanned work.</div>'
    else:
        tasks = "".join(
            f'<div class="gf-tk"><span class="gf-tid">{_esc(t.id)}</span>{_esc(t.title)}'
            f'<span class="gf-pill">{_esc(t.status)}</span>'
            f'<span class="gf-item">{_esc(t.item)}</span></div>'
            for t in row.tasks
        )
    return f'<div class="gf-exp">{criterion}{tasks}</div>'


_ICONS = {"critical": ("crit", "!"), "serious": ("ser", "▲"), "warning": ("warn", "•")}


def _drift(drift) -> str:
    """The diff between the approved version and now, behind a disclosure.

    Collapsed because the panel's job is to say what needs attention, not to
    be a diff viewer; open because the next question is always "changed how?".
    Works with JS disabled — <details> is markup, not script.
    """
    if drift is None:
        return ""
    if drift.lines is None:
        # Never an empty diff. "Nothing changed" and "the comparison could not
        # be made" are opposite claims about whether the approval still holds.
        return ('<p class="gf-isub gf-dwhy">Cannot show what changed: '
                f'{_esc(drift.why)}.</p>')
    rows = []
    for line in drift.lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        cls = ("add" if line.startswith("+")
               else "del" if line.startswith("-")
               else "at" if line.startswith("@@") else "ctx")
        rows.append(f'<div class="gf-dl {cls}">{_esc(line)}</div>')
    more = (f'<div class="gf-dl ctx">… {drift.truncated} more line'
            f'{"" if drift.truncated == 1 else "s"}; see git for the rest</div>'
            if drift.truncated else "")
    return (
        '<details class="gf-drift"><summary>What changed since '
        f'{_esc(drift.commit)}</summary>'
        f'<div class="gf-diff">{"".join(rows)}{more}</div></details>'
    )


def _attention(state) -> str:
    if not state.findings:
        return _card("Needs attention", '<p class="gf-none">Nothing right now.</p>')
    # Drift is attached to the finding that announces it. "requirements.md
    # changed after sign-off" raises exactly one question — changed how? —
    # and before this the answer was "leave the dashboard and go to git".
    by_artifact = {d.artifact: d for d in getattr(state, "drift", ())}
    items = []
    for finding in state.findings:
        css, glyph = _ICONS[finding.severity]
        artifact = finding.label.split(" ")[0]
        extra = _drift(by_artifact.get(artifact)) if "changed after sign-off" in finding.label else ""
        items.append(
            f'<div class="gf-item"><div class="gf-ico {css}">{glyph}</div><div>'
            f'<div class="gf-itxt"><span class="gf-lbl">{_esc(finding.label)}</span></div>'
            f'<div class="gf-isub">{_esc(finding.detail)}</div>{extra}</div></div>'
        )
    return _card("Needs attention", f'<div class="gf-att">{"".join(items)}</div>')


def _rail(state) -> str:
    """The right column of the feed-led row: a compact gate ladder (the same
    evidence `_gates` draws as the full-width spine, laid out as a vertical
    list instead), two headline readouts, and the attention panel.

    This is the reversal the layout rework turns on: the gate ladder used to
    be the page's hero because sequential approvals each carrying evidence
    *is* the methodology's claim. Here it is a rail, because on a page opened
    every morning the gates are already known and the feed to its left is the
    news. Both readings are correct for their moment."""
    stations = []
    for index, gate in enumerate(state.gates):
        css, glyph = _GATE_CSS[gate.state]
        mark = glyph or str(index)
        if gate.state == "approved":
            sub = f"{_esc(gate.date)} · {_esc(gate.commit[:7])}"
        elif gate.state == "changed":
            sub = (f"{_esc(gate.artifact)} changed since {_esc(gate.commit[:7])}"
                   " — the approval no longer covers it")
        elif gate.state == "unverifiable":
            sub = f"cannot verify: commit {_esc(gate.commit[:7])} is not in this repository"
        elif gate.state == "current" and state.days_in_gate is not None:
            sub = f"{state.days_in_gate} days in gate"
        else:
            sub = "&mdash;"
        stations.append(
            f'<div class="gf-rs {css}"><div class="gf-num">{mark}</div>'
            f'<div><div class="gf-rn">{_esc(gate.name)}</div>'
            f'<div class="gf-rsub">{sub}</div></div></div>'
        )

    readable = state.tasks.present and state.tasks.header_ok
    due = state.tasks.tasks or analyse.tasks_expected(state.signoffs)
    if readable and due:
        counts = analyse.count(state.tasks.tasks)
        tasks_value = f"{counts.done} / {counts.total_active}"
    else:
        tasks_value = "—"

    gates_card = (
        '<div class="gf-card"><div class="gf-h">Gates</div>'
        f'<div class="gf-rail">{"".join(stations)}</div>'
        '<div class="gf-railstats">'
        f'<div class="gf-stat"><div class="gf-slabel">Tasks complete</div>'
        f'<div class="gf-sval">{_esc(tasks_value)}</div></div>'
        f'<div class="gf-stat"><div class="gf-slabel">Needs attention</div>'
        f'<div class="gf-sval">{len(state.findings)}</div></div>'
        "</div></div>"
    )
    return f'<div>{gates_card}{_attention(state)}</div>'


def _stat(label: str, value: str, sub: str, muted: bool = False) -> str:
    cls = "gf-sval muted" if muted else "gf-sval"
    return (
        f'<div class="gf-stat"><div class="gf-slabel">{_esc(label)}</div>'
        f'<div class="{cls}">{_esc(value)}</div>'
        f'<div class="gf-ssub">{_esc(sub)}</div></div>'
    )


def _statrow(state) -> str:
    """Four headline numbers. Every one of them refuses to show a figure it
    cannot stand behind: an unreadable tasks.md yields an em-dash and a reason,
    never a zero."""
    readable = state.tasks.present and state.tasks.header_ok
    # A valid but empty tasks.md before the Design gate is not "zero tasks done"
    # — the file has not been produced yet. Rendering 0 / 0 states a completion
    # ratio for work that has not been planned.
    not_due_yet = readable and not state.tasks.tasks and not analyse.tasks_expected(state.signoffs)

    if readable and not not_due_yet:
        counts = analyse.count(state.tasks.tasks)
        done = _stat("Tasks complete", f"{counts.done} / {counts.total_active}",
                     "dropped excluded" if counts.dropped else "of active scope")
        left = _stat("Remaining", str(counts.remaining), "not done, not dropped")
    else:
        if not_due_yet:
            reason = "produced at gate 2"
        elif not state.tasks.present:
            reason = "no tasks.md yet"
        else:
            reason = "tasks.md unreadable"
        done = _stat("Tasks complete", "—", reason, muted=True)
        left = _stat("Remaining", "—", reason, muted=True)

    if state.reqs.present and readable and not not_due_yet:
        rows = analyse.coverage(state.reqs, state.tasks)
        covered = sum(1 for r in rows if r.tasks)
        cov = _stat("Coverage", f"{covered} / {len(rows)}", "requirements with tasks")
    else:
        # Absent, unreadable and not-yet-due are three different facts and must
        # not share copy.
        if not state.reqs.present:
            why = "no requirements.md yet"
        elif not_due_yet:
            why = "tasks produced at gate 2"
        elif not state.tasks.present:
            why = "no tasks.md yet"
        else:
            why = "tasks.md unreadable"
        cov = _stat("Coverage", "—", why, muted=True)

    worst = state.findings[0].severity if state.findings else None
    att = _stat(
        "Needs attention",
        str(len(state.findings)) if state.findings else "0",
        f"most severe: {worst}" if worst else "nothing outstanding",
        muted=not state.findings,
    )
    return f'<div class="gf-stats">{done}{left}{cov}{att}</div>'


def _narrative(state) -> str:
    """The editorial line. Assembled only from figures already verified
    elsewhere on the page, and it says when it cannot see something rather
    than narrating around the gap."""
    if not state.tasks.present:
        sentence = "No task list yet — <em>tasks.md</em> is produced at gate 2."
    elif not state.tasks.header_ok:
        sentence = "Task state <em>cannot be read</em> — tasks.md's header was not recognised."
    elif not state.tasks.tasks and not analyse.tasks_expected(state.signoffs):
        sentence = (
            f"{_esc(_phase(state))} — the task list is <em>not yet produced</em>. "
            "It arrives at gate 2, once design is signed off."
        )
    else:
        counts = analyse.count(state.tasks.tasks)
        phase = _phase(state).lower()
        sentence = (
            f"{_esc(_phase(state))} — <em>{counts.done} of {counts.total_active}</em> tasks "
            f"complete, {counts.remaining} remaining"
        )
        if counts.blocked:
            sentence += f", <em>{counts.blocked} blocked</em>"
        if counts.dropped:
            sentence += f". {counts.dropped} dropped from scope"
        sentence += "."
        del phase
    critical = [f for f in state.findings if f.severity == "critical"]
    if critical:
        sentence += f" <em>{len(critical)}</em> critical finding{'s' if len(critical) != 1 else ''} below."
    return (
        '<div class="gf-card"><div class="gf-h">Where we are</div>'
        f'<p class="gf-narr">{sentence}</p></div>'
    )


def _nav(siblings, slug) -> str:
    """Navigation, and only when there is somewhere to go.

    `siblings` is None in single-root mode, where a link to a portfolio that
    does not exist would be a dead end — the same rule the rest of this page
    follows about not rendering a state that is not real.

    A switcher rather than only a back link: someone running several
    engagements moves between them far more often than they look at the index,
    and making them go via the index to do it is two clicks for no reason.
    """
    if not siblings or len(siblings) < 2:
        return ""
    others = "".join(
        f'<a class="gf-eng{" on" if s == slug else ""}" href="/e/{_esc(s)}">{_esc(name)}</a>'
        for s, name in siblings
    )
    return (
        '<nav class="gf-nav" aria-label="Engagements">'
        '<a class="gf-up" href="/">\u2190 All engagements</a>'
        f'<span class="gf-navsep">·</span>{others}</nav>'
    )


def body(state, siblings=None, slug=None) -> str:
    """Masthead, then the feed beside the gate rail, then tasks, then
    coverage.

    Feed-led, and deliberately so: this reverses the earlier order, where the
    gate spine ran full-width as the hero because sequential approvals each
    carrying evidence *is* the methodology's claim. That reading still holds
    on a page opened to ask where things stand. This page is opened daily —
    the gates are already known, and what moved since last time is the news.
    The rail (`_rail`) keeps every gate visible, just no longer as the hero.
    """
    return (
        '<div class="gf"><div class="gf-app">'
        + _nav(siblings, slug)
        + _topbar(state)
        + '<div class="gf-row">' + _feed(state) + _rail(state) + "</div>"
        + _tasks_panel(state)
        + _coverage(state)
        + "</div></div>"
    )


POLL_JS = """
(function () {
  var root = document.getElementById('root');
  var lastHash = null;
  var banner = null;

  function showBanner(message) {
    if (!banner) {
      banner = document.createElement('div');
      banner.style.cssText = 'padding:8px 12px;background:#d03b3b;color:#fff;font:12px sans-serif;';
      document.body.insertBefore(banner, document.body.firstChild);
    }
    banner.textContent = message;
  }

  function hideBanner() {
    if (banner) {
      banner.remove();
      banner = null;
    }
  }

  function poll() {
    // On /e/<slug> the page must poll its own engagement, not whichever one
    // the server would pick by default.
    var slug = (location.pathname.match(/^\\/e\\/([^/]+)/) || [])[1];
    fetch('/api/state' + (slug ? '?e=' + encodeURIComponent(slug) : ''))
      .then(function (response) {
        if (!response.ok) {
          throw new Error('bad response');
        }
        return response.json();
      })
      .then(function (data) {
        if (typeof data.hash !== 'string' || typeof data.html !== 'string') {
          throw new Error('malformed state response');
        }
        hideBanner();
        if (data.hash !== lastHash) {
          lastHash = data.hash;
          root.innerHTML = data.html;
          document.dispatchEvent(new Event('gf:rendered'));
        }
      })
      .catch(function () {
        showBanner('lost contact with dashboard server');
      });
  }

  poll();
  setInterval(poll, 2000);
})();
"""


_SEVERITY_TOKEN = {"critical": "--critical", "serious": "--serious", "warning": "--warning"}


def _index_row(slug: str, state) -> str:
    href = f"/e/{_esc(slug)}"
    if not state.engagement.present:
        # Listed, not dropped. Silently omitting a path that turned out not to
        # be an engagement would let the reader believe they were looking at
        # their whole portfolio.
        return (
            f'<a class="gf-erow" href="{href}">'
            f'<div><div class="gf-ename muted">{_esc(slug)}</div>'
            f'<div class="gf-eslug">{_esc(slug)}</div></div>'
            '<div class="gf-emeta">Not an engagement — no docs/engagement/engagement.md</div>'
            '<div class="gf-emono">—</div>'
            '<div class="gf-emeta">—</div></a>'
        )

    readable = state.tasks.present and state.tasks.header_ok
    due = state.tasks.tasks or analyse.tasks_expected(state.signoffs)
    if readable and due:
        counts = analyse.count(state.tasks.tasks)
        tasks_cell = f"{counts.done} / {counts.total_active}"
    else:
        tasks_cell = "—"

    if state.findings:
        worst = state.findings[0].severity
        token = _SEVERITY_TOKEN.get(worst, "--ink-3")
        attention = (
            f'<span class="gf-edot" style="background:var({token})"></span>'
            f"{len(state.findings)} {_esc(worst)}"
        )
    else:
        attention = "nothing outstanding"

    return (
        f'<a class="gf-erow" href="{href}">'
        f'<div><div class="gf-ename">{_esc(_client(state))}</div>'
        f'<div class="gf-eslug">{_esc(slug)}</div></div>'
        f'<div class="gf-emeta">{_esc(_phase(state))}</div>'
        f'<div class="gf-emono">{_esc(tasks_cell)}</div>'
        f'<div class="gf-emeta">{attention}</div></a>'
    )


def index_body(entries) -> str:
    """The portfolio. One row per root given on the command line, in that
    order, including any that turned out not to be engagements."""
    count = len(entries)
    rows = "".join(_index_row(slug, state) for slug, state in entries)
    return (
        '<div class="gf"><div class="gf-app">'
        '<header class="gf-mast"><div>'
        '<div class="gf-eyebrow">Portfolio</div>'
        f'<h1 class="gf-title">{count} engagement{"s" if count != 1 else ""}</h1>'
        '<span class="gf-shape">Read-only. Reload to refresh.</span>'
        "</div>" + _toggle() + "</header>"
        '<div class="gf-card"><div class="gf-h">Engagements</div>'
        f'<div class="gf-elist">{rows}</div></div>'
        "</div></div>"
    )


THEME_JS = """
(function () {
  var KEY = 'gf-theme';
  function apply(mode) {
    var el = document.documentElement;
    if (mode === 'light' || mode === 'dark') { el.setAttribute('data-theme', mode); }
    else { el.removeAttribute('data-theme'); }
    var buttons = document.querySelectorAll('[data-set-theme]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed',
        String(buttons[i].getAttribute('data-set-theme') === mode));
    }
  }
  var saved;
  try { saved = localStorage.getItem(KEY); } catch (e) { saved = null; }
  apply(saved || 'auto');
  document.addEventListener('click', function (event) {
    var button = event.target.closest && event.target.closest('[data-set-theme]');
    if (!button) { return; }
    var mode = button.getAttribute('data-set-theme');
    try { localStorage.setItem(KEY, mode); } catch (e) { /* private mode */ }
    apply(mode);
  });
  // The poll replaces #root, so the buttons are new elements each time.
  document.addEventListener('gf:rendered', function () {
    var mode;
    try { mode = localStorage.getItem(KEY); } catch (e) { mode = null; }
    apply(mode || 'auto');
  });
})();
"""


FEED_JS = """
(function () {
  // Scoped by engagement, exactly as POLL_JS scopes its fetch URL. /e/<slug>
  // routes several engagements through one origin, so an origin-wide key let
  // alpha's marker be looked up against beta's rows, match nothing, and mark
  // every row in beta new — "247 new since your last visit" on a page the
  // reader had never opened.
  var slug = (location.pathname.match(/^\\/e\\/([^/]+)/) || [])[1];
  var KEY = 'gf-last-seen' + (slug ? ':' + slug : '');
  var root = document;
  function lastSeen() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function remember(commit) {
    try { localStorage.setItem(KEY, commit); } catch (e) { /* private mode */ }
  }
  // Read ONCE, before anything writes it, and held for the life of the page.
  // `apply` runs again on every `gf:rendered`, so re-reading storage there
  // would compare the feed against a marker this same page had just advanced
  // — the baseline chasing the newest row, and "1 new" forever.
  var SEEN = lastSeen();
  function apply(range) {
    var rows = root.querySelectorAll('.gf-ev');
    var seen = SEEN;
    var shown = 0, isNew = 0;
    var cutoff = Date.now() - 7 * 864e5;
    var passedSeen = false;
    rows.forEach(function (row) {
      // The marker row is the last row already seen, so it is not itself new.
      // Deciding that BEFORE `fresh` is the whole fix: evaluated after, the
      // marker row counted as new and `isNew` could never reach 0.
      if (seen && row.getAttribute('data-commit') === seen) { passedSeen = true; }
      var fresh = seen ? !passedSeen : false;
      row.classList.toggle('gf-new', fresh);
      if (fresh) { isNew++; }
      var visible = range === 'all'
        || (range === 'visit' ? (seen ? fresh : Date.parse(row.getAttribute('data-when')) >= cutoff)
                              : Date.parse(row.getAttribute('data-when')) >= cutoff);
      row.classList.toggle('hide', !visible);
      if (visible) { shown++; }
    });
    // Move the divider after the last new row. Only the client knows where
    // that boundary is.
    var divider = root.getElementById('gf-earlier');
    var feed = root.getElementById('gf-feed');
    if (divider && feed) {
      var newRows = feed.querySelectorAll('.gf-ev.gf-new');
      if (range === 'visit' && newRows.length && newRows.length < rows.length) {
        newRows[newRows.length - 1].after(divider);
        divider.classList.remove('hide');
      } else {
        divider.classList.add('hide');
      }
    }
    var label = root.getElementById('gf-feedcount');
    if (label) {
      if (range === 'visit' && !seen) {
        label.textContent = 'No previous visit recorded — showing the last 7 days';
      } else if (range === 'visit') {
        label.textContent = isNew + ' new since your last visit';
      } else if (range === '7') {
        label.textContent = shown + ' events · last 7 days';
      } else {
        label.textContent = shown + ' events · all time';
      }
    }
  }
  function filterTasks(status) {
    var none = root.querySelector('.gf-nomatch');
    var n = 0;
    root.querySelectorAll('#gf-tasklist .gf-tk').forEach(function (row) {
      var vis = status === 'all' || row.getAttribute('data-status') === status;
      row.classList.toggle('hide', !vis);
      if (vis) { n++; }
    });
    if (none) { none.hidden = n !== 0; }
  }
  // What the reader is currently looking at. POLL_JS replaces #root's
  // innerHTML whenever the engagement changes and then fires gf:rendered, so
  // `start` runs again on live content — and `start` re-applying the DEFAULTS
  // was the bug: someone reading "All" history had the page snap back to
  // "Since last visit" the moment anyone committed, mid-scroll, every two
  // seconds. Re-applying the CHOICE is what the gf:rendered binding was for.
  var curRange = 'visit', curFilter = 'all';
  root.addEventListener('click', function (event) {
    var chip = event.target.closest && event.target.closest('[data-range],[data-filter]');
    if (!chip) { return; }
    if (chip.hasAttribute('data-range')) {
      curRange = chip.getAttribute('data-range');
      root.querySelectorAll('[data-range]').forEach(function (c) {
        c.classList.toggle('on', c === chip);
      });
      apply(curRange);
    } else {
      curFilter = chip.getAttribute('data-filter');
      root.querySelectorAll('[data-filter]').forEach(function (c) {
        c.classList.toggle('on', c === chip);
      });
      filterTasks(curFilter);
    }
  });
  function markOn(attr, value) {
    root.querySelectorAll('[' + attr + ']').forEach(function (c) {
      c.classList.toggle('on', c.getAttribute(attr) === value);
    });
  }
  function start() {
    // Defaults must match what the server already rendered with no rows
    // hidden and no chip highlighted: "all tasks" and "since your last
    // visit" (the honest first-visit fallback, not an arbitrary status).
    // Marking the matching chip 'on' keeps the highlighted state truthful
    // about what is actually being shown.
    apply(curRange);
    filterTasks(curFilter);
    markOn('data-range', curRange);
    markOn('data-filter', curFilter);
  }
  start();
  document.addEventListener('gf:rendered', start);
  // The baseline advances exactly once per page load, and deliberately NOT
  // from `start`. `gf:rendered` fires about 50ms after every load — POLL_JS
  // opens with lastHash null, so the first response always differs and #root
  // is always replaced — and again on every change after that. Remembering
  // there moved the marker to the newest row continuously: a tab left open
  // overnight absorbed each poll's newest sha as it arrived and read "1 new
  // since your last visit" in the morning whatever had landed. That is the
  // manufactured quiet week, which is the one thing this panel exists to
  // prevent.
  //
  // With no rows there is nothing that could have been seen, so nothing is
  // written and the next load still compares against the real last visit.
  var newest = root.querySelector('.gf-ev');
  if (newest) { remember(newest.getAttribute('data-commit')); }
})();
"""


def page(state, siblings=None, slug=None) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(_client(state))} — Engagement</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div id="root">{body(state, siblings, slug)}</div>'
        f"<script>{POLL_JS}</script><script>{THEME_JS}</script>"
        f"<script>{FEED_JS}</script></body></html>"
    )


def index_page(entries) -> str:
    """The portfolio as a full document. Deliberately not polled — it is a
    jumping-off point, and a stale row is corrected by opening the engagement,
    which does poll."""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Engagements</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div id="root">{index_body(entries)}</div>'
        f"<script>{THEME_JS}</script></body></html>"
    )
