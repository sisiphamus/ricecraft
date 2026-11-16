"""Landing flow: the plain page opens first, its Login button leads to the game's title
screen, and Join World starts the walk. The plain page states the event details and
the sponsor status in their own clearly labelled sections.

python3 tests/flow.py
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

URL = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
results = []

def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''), flush=True)

async def run(vp, touch, tag):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS)
        ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=touch)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL, timeout=120000)
        await pg.wait_for_timeout(3000)
        check(f'{tag} the plain page opens first', await pg.evaluate("mode==='lame' && !document.querySelector('#lame').classList.contains('hidden')"))
        check(f'{tag} the title screen is not showing yet', await pg.evaluate("document.querySelector('#title').classList.contains('hidden')"))
        text = await pg.evaluate("document.querySelector('#lame').innerText")
        for needle in ['Feb 5', 'Rice University', '200', 'Sponsors']:
            check(f'{tag} plain page mentions {needle}', needle.upper() in text.upper())  # headings are shown in capitals
        det = await pg.evaluate("!!document.querySelector('#lame #details') && document.querySelector('#lame #details').innerText")
        check(f'{tag} plain page has an event details section', bool(det) and all(w in det.upper() for w in ('WHEN','WHERE','APPLY','SPONSORS')), (det or '')[:80].replace('\n', ' / '))
        sp = await pg.evaluate("!!document.querySelector('#lame #sponsors') && document.querySelector('#lame #sponsors').innerText")
        check(f'{tag} plain page has its own sponsors section', bool(sp) and 'SPONSOR' in sp.upper() and 'ANNOUNCED' in sp.upper(), (sp or '')[:80].replace('\n', ' / '))
        login = pg.locator('#lame .lh [data-l="login"]')
        check(f'{tag} a Login button is in the header', await login.count() == 1 and 'LOG' in (await login.inner_text()).upper())
        await login.click()
        await pg.wait_for_timeout(1500)
        check(f'{tag} Login opens the title screen', await pg.evaluate("mode==='title' && !document.querySelector('#title').classList.contains('hidden') && document.querySelector('#lame').classList.contains('hidden')"))
        await pg.wait_for_function('world3', timeout=180000)
        await pg.click('#joinBtn')
        await pg.wait_for_function("mode==='world'", timeout=60000)
        check(f'{tag} Join World starts the walk', True)
        check(f'{tag} no script errors', not errs, '; '.join(errs[:2]))
        await b.close()

async def main():
    await run({'width': 1280, 'height': 720}, False, 'laptop')
    await run({'width': 390, 'height': 844}, True, 'phone')
    print(f"\n{sum(results)} passed, {len(results)-sum(results)} failed")
    sys.exit(0 if all(results) else 1)

asyncio.run(main())
