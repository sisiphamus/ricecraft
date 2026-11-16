"""Phone checks: the walk does not jump when the browser bar hides, swipes land on a sign,
the on-screen pieces do not sit on top of each other, and long presses do not pop up menus.

python3 tests/phone.py
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

URL = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
results = []

def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''), flush=True)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS)
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL, timeout=120000)
        await pg.wait_for_function('world3', timeout=180000)
        # the plain page opens first; Login leads to the game's title screen
        await pg.click('#lame .lh [data-l="login"]')
        await pg.wait_for_timeout(800)
        await pg.tap('#joinBtn')
        await pg.wait_for_function("mode==='world'", timeout=60000)
        await pg.wait_for_timeout(2500)

        # 1. the browser bar hiding (height change only) must not move the walk
        before = await pg.evaluate('STEP')
        await pg.set_viewport_size({'width': 390, 'height': 760})
        await pg.wait_for_timeout(1500)
        after = await pg.evaluate('STEP')
        reach = await pg.evaluate('document.documentElement.scrollHeight-innerHeight >= STEP*(STATIONS.length-1)-1')
        check('the last sign is still reachable after the bar hides', reach)
        check('walk length stays put when the browser bar hides', before == after, f'{before} -> {after}')
        await pg.set_viewport_size({'width': 390, 'height': 900})
        await pg.wait_for_timeout(1500)
        reach2 = await pg.evaluate('document.documentElement.scrollHeight-innerHeight >= STEP*(STATIONS.length-1)-1')
        check('the last sign is reachable when the bar shows again', reach2)
        await pg.set_viewport_size({'width': 390, 'height': 844})
        await pg.wait_for_timeout(1500)

        # 2. a swipe that stops between two signs settles on a sign
        step = await pg.evaluate("STEP")
        await pg.mouse.move(195, 400)
        await pg.mouse.wheel(0, step * 0.6)
        await pg.wait_for_timeout(2500)
        y = await pg.evaluate('scrollY')
        k = y / step
        check('a half swipe settles on a sign', abs(k - round(k)) < 0.02, f'scrollY {y:.0f}, step {step:.0f}')

        # 3. nothing on the screen overlay sits on top of anything else
        boxes = await pg.evaluate('''(()=>{ const out={}; for(const id of ['info','menuBtn','hotbar','mineHint','walkHint','lameBtn','xp','toasts']){
            const el=document.getElementById(id); if(!el) continue; const cs=getComputedStyle(el); if(cs.display==='none'||cs.visibility==='hidden'||+cs.opacity===0||el.classList.contains('gone')) continue;
            const r=el.getBoundingClientRect(); if(r.width&&r.height) out[id]=[r.left,r.top,r.right,r.bottom]; } return out; })()''')
        names = list(boxes)
        clashes = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, c = boxes[names[i]], boxes[names[j]]
                if a[0] < c[2] - 1 and c[0] < a[2] - 1 and a[1] < c[3] - 1 and c[1] < a[3] - 1:
                    clashes.append(f'{names[i]}/{names[j]}')
        check('no on-screen pieces overlap', not clashes, ', '.join(clashes))
        inside = all(0 <= v[0] and v[2] <= 390 for v in boxes.values())
        check('all on-screen pieces fit the screen width', inside)

        # 4. long press to mine does not open the text or image menu
        # Chromium does not report -webkit-touch-callout, so look for the rule in the page's CSS (Safari reads it)
        callout = await pg.evaluate("[...document.querySelectorAll('style')].some(s=>/body\\.in-world\\{[^}]*-webkit-touch-callout:none/.test(s.textContent))")
        sel = await pg.evaluate("getComputedStyle(document.body).userSelect")
        check('long press shows no pop-up menu', callout and sel == 'none', f'callout rule {callout}, select {sel}')

        # 5. the phone draws at a lighter resolution so it stays smooth
        pr = await pg.evaluate('renderer.getPixelRatio()')
        check('phone draws at 1.25x or less', pr <= 1.25, f'{pr}')
        check('no script errors', not errs, '; '.join(errs[:2]))
        await b.close()
    print(f"\n{sum(results)} passed, {len(results)-sum(results)} failed")
    sys.exit(0 if all(results) else 1)

asyncio.run(main())
