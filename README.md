# RiceCraft

The website for the Rice Spring Hack, Feb 5 to 7, 2027, at Rice University in Houston.

Open the site, press Join World, and scroll to walk through a block world. Big wooden signs carry the event details. Hold on any block (or a sign) to mine it, and craft items at the crafting tables to unlock the Schedule, Sponsors and Apply pages. The Lame mode button switches to a plain web page with the same details.

Everything is in one file, `index.html`, with three.js loaded from cdnjs. All art and music are drawn and generated in code. Fan-made; not affiliated with Mojang or Microsoft.

## Run locally

    python3 -m http.server 8000

then open http://localhost:8000.

## Tests

    python3 tests/e2e.py

Needs Python Playwright with Chromium.
