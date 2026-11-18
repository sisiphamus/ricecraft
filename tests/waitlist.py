"""Waitlist: buttons on the plain page, title screen and in-game menu open a game-style
form with name and email; bad input is refused; a good entry is posted to the Google Form
with the right fields and the player sees a success screen.

python3 tests/waitlist.py   (the Google Form is intercepted; nothing is really sent)
"""
import asyncio, sys, pathlib, urllib.parse
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
OUT = ROOT / 'tests' / 'out'; OUT.mkdir(exist_ok=True)
ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
results = []

async def shot(pg, name):
    try:
        await pg.screenshot(path=str(OUT / name), timeout=120000)
    except Exception as e:
        print('  (screenshot skipped:', name, str(e)[:60], ')')

def check(name, ok, detail=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''), flush=True)

async def run(vp, touch, tag):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS)
        ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=touch)
        pg = await ctx.new_page()
        errs, posts = [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        async def grab(route):
            posts.append(route.request.post_data or '')
            await route.fulfill(status=200, body='ok')
        await pg.route('**/formResponse', grab)
        await pg.goto(URL, timeout=120000)
        await pg.wait_for_timeout(2500)

        for sel, where in [('#lame .lh [data-l="waitlist"]', 'header'), ('#lame .hero [data-l="waitlist"]', 'hero'), ('#lame .apply [data-l="waitlist"]', 'apply section')]:
            check(f'{tag} plain page has a waitlist button in the {where}', await pg.locator(sel).count() == 1)
        check(f'{tag} plain page no longer says "applications open soon"', 'OPEN SOON' not in (await pg.evaluate("document.querySelector('#lame').innerText")).upper())
        check(f'{tag} event details offer the waitlist under Apply', await pg.locator('#lame #details [data-l="waitlist"]').count() == 1)

        await pg.click('#lame .hero [data-l="waitlist"]')
        await pg.wait_for_timeout(400)
        check(f'{tag} the waitlist form opens with name and email fields', await pg.locator('#wlName').is_visible() and await pg.locator('#wlEmail').is_visible())
        box = await pg.locator('.wl').bounding_box()
        check(f'{tag} the form fits on screen', box and box['x'] >= 0 and box['x'] + box['width'] <= vp['width'] and box['y'] >= 0 and box['y'] + box['height'] <= vp['height'], str(box))
        await shot(pg, f'waitlist-{tag}-form.png')

        await pg.click('#wlGo'); await pg.wait_for_timeout(200)
        check(f'{tag} an empty name is refused', 'name' in (await pg.inner_text('#wlMsg')).lower() and not posts)
        await pg.fill('#wlName', 'Test Player'); await pg.fill('#wlEmail', 'not-an-email')
        await pg.click('#wlGo'); await pg.wait_for_timeout(200)
        check(f'{tag} a bad email is refused', 'email' in (await pg.inner_text('#wlMsg')).lower() and not posts)
        await pg.fill('#wlEmail', '')
        await pg.locator('#wlEmail').type('test.player@rice.edu')
        await pg.click('#wlGo'); await pg.wait_for_timeout(800)
        q = urllib.parse.parse_qs(posts[0]) if posts else {}
        check(f'{tag} one entry is posted with the name and email', len(posts) == 1 and q.get('entry.1501410818') == ['Test Player'] and q.get('entry.1764343551') == ['test.player@rice.edu'], posts[:1])
        ok = await pg.locator('.wl-ok').count() == 1
        check(f'{tag} the player sees "on the list"', ok and 'ON THE LIST' in (await pg.inner_text('.wl-ok')).upper())
        await shot(pg, f'waitlist-{tag}-done.png')
        await pg.click('.wl-ok [data-a="cancel"]'); await pg.wait_for_timeout(300)
        check(f'{tag} Done closes the form', await pg.evaluate("document.querySelector('#gui').classList.contains('hidden') && guiMode===null"))

        await pg.click('#lame .lh [data-l="login"]'); await pg.wait_for_timeout(1200)
        check(f'{tag} the title screen has a Join Waitlist button', await pg.locator('#wlBtn').is_visible())
        await shot(pg, f'waitlist-{tag}-title.png')
        await pg.click('#wlBtn'); await pg.wait_for_timeout(300)
        check(f'{tag} the title button opens the form', await pg.locator('#wlName').is_visible())
        await pg.click('.wl [data-a="cancel"]'); await pg.wait_for_timeout(300)
        check(f'{tag} Cancel closes it with nothing sent', await pg.evaluate("guiMode===null") and len(posts) == 1)

        await pg.wait_for_function('world3', timeout=180000)
        await pg.click('#joinBtn')
        await pg.wait_for_function("mode==='world'", timeout=60000); await pg.wait_for_timeout(1500)
        await pg.click('#menuBtn'); await pg.wait_for_timeout(300)
        wl = pg.locator('#gui [data-a="waitlist"]')
        check(f'{tag} the Game Menu has Join Waitlist', await wl.count() == 1)
        await wl.click(); await pg.wait_for_timeout(300)
        await pg.fill('#wlName', 'In Game'); await pg.fill('#wlEmail', 'ingame@example.com')
        await shot(pg, f'waitlist-{tag}-world.png')
        await pg.keyboard.press('Enter') if not touch else await pg.click('#wlGo')
        await pg.wait_for_timeout(800)
        check(f'{tag} joining from inside the world works', len(posts) == 2 and await pg.locator('.wl-ok').count() == 1)
        await pg.evaluate("openBook('apply')"); await pg.wait_for_timeout(300)
        check(f'{tag} the Apply page offers the waitlist', await pg.locator('.book [data-a="waitlist"]').count() == 1)
        check(f'{tag} the Apply page no longer says "open soon"', 'OPEN SOON' not in (await pg.inner_text('.book')).upper())
        await pg.click('.book [data-a="waitlist"]'); await pg.wait_for_timeout(300)
        check(f'{tag} ...and it opens the form', await pg.locator('#wlName').is_visible())
        check(f'{tag} no script errors', not errs, '; '.join(errs[:2]))
        await b.close()

async def main():
    await run({'width': 1280, 'height': 720}, False, 'laptop')
    await run({'width': 390, 'height': 844}, True, 'phone')
    print(f"\n{sum(results)} passed, {len(results)-sum(results)} failed")
    sys.exit(0 if all(results) else 1)

asyncio.run(main())
