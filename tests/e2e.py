"""End to end checks for RiceCraft, run in a real Chromium.

python3 tests/e2e.py [d|m]   (default: both laptop and phone)
WebGL runs on SwiftShader here, so frames are slow; timeouts are generous.
"""
import asyncio, sys, pathlib
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / 'index.html').as_uri()
OUT = ROOT / 'tests' / 'out'
ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
SIZES = {'d': ({'width': 1280, 'height': 720}, False), 'm': ({'width': 390, 'height': 844}, True)}
results = []

def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''), flush=True)

async def go_stop(pg, i):
    await pg.evaluate(f'window.scrollTo(0,{i}*STEP)')
    await pg.wait_for_function(f'Math.abs(sNow-{i})<0.02', timeout=240000)
    await pg.wait_for_timeout(1200)

async def run(which):
    vp, touch = SIZES[which]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS)
        ctx = await b.new_context(viewport=vp, has_touch=touch, is_mobile=touch)
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL, timeout=120000)
        await pg.wait_for_function('world3', timeout=120000)
        await pg.click('#joinBtn')
        await pg.wait_for_function("mode==='world'", timeout=60000)
        await pg.wait_for_timeout(2500)
        # 1. every crafting/enchanting table is fully on screen, above the item bar, and big enough to see
        n = await pg.evaluate('STATIONS.length')
        for i in range(n):
            if not await pg.evaluate(f'STATIONS[{i}].tables.length'):
                continue
            await go_stop(pg, i)
            OUT.mkdir(exist_ok=True)
            await pg.screenshot(path=str(OUT / f'{which}-stop{i}.png'), timeout=120000)
            info = await pg.evaluate(f'''(()=>{{ const hb=document.querySelector('#hotbar').getBoundingClientRect();
              return STATIONS[{i}].tables.map(t=>{{ const pts=[]; for(const dx of [-.5,.5]) for(const dy of [-.5,.5]) for(const dz of [-.5,.5]) pts.push(screenOf(t.x+dx,t.y+dy,t.z+dz));
                const xs=pts.map(p=>p[0]), ys=pts.map(p=>p[1]); const r={{l:Math.min(...xs),r:Math.max(...xs),t:Math.min(...ys),b:Math.max(...ys)}};
                return {{inside: r.l>=0&&r.r<=innerWidth&&r.t>=0&&r.b<=hb.top, area:(r.r-r.l)*(r.b-r.t)/(innerWidth*innerHeight), r}}; }}); }})()''')
            for k, t in enumerate(info):
                check(f'{which} stop {i} table {k} on screen and above item bar', t['inside'], f"box {[round(v) for v in t['r'].values()]}")
                check(f'{which} stop {i} table {k} big enough', t['area'] >= 0.03, f"{t['area']*100:.1f}% of screen")
        # 2. signs can be mined and drop an item that keeps the text
        await go_stop(pg, 0)
        await pg.wait_for_timeout(1500)
        cx, cy = await pg.evaluate('screenOf(STATIONS[0].center.x,STATIONS[0].center.y,STATIONS[0].center.z)')
        # SwiftShader draws about 3 frames a second, so step the game loop by hand with real-sized time steps
        await pg.mouse.move(cx, cy); await pg.mouse.down()
        await pg.evaluate("(()=>{ for(let k=0;k<40;k++) frame3(0.05, performance.now()); })()")
        await pg.mouse.up()
        await pg.wait_for_timeout(1500)
        gone = await pg.evaluate('!STATIONS[0].group.visible')
        has = await pg.evaluate("inv.some(s=>s&&s.id.startsWith('sign'))")
        check(f'{which} mining the welcome sign removes it', gone)
        check(f'{which} mined sign lands in the item bar', has)
        # 2b. the sign item opens a page with the sign's words
        await pg.evaluate("openBook(inv.find(s=>s&&s.id.startsWith('sign')).id.replace('sign_','sign_'))") if has else None
        if has:
            await pg.wait_for_timeout(500)
            words = await pg.evaluate("document.querySelector('#gui').innerText")
            check(f'{which} sign item shows the event dates', 'Feb 5' in words)
            await pg.evaluate("closeGui()")
        # 2c. diamonds look like diamonds: the item is named Diamond
        check(f'{which} gem item is a Diamond', await pg.evaluate("ITEMS.gem.name==='Diamond'"))
        # 3. lame mode opens and carries the facts
        await pg.evaluate("enterLame()")
        await pg.wait_for_function("mode==='lame'", timeout=60000)
        await pg.wait_for_timeout(2000)
        txt = await pg.evaluate("document.querySelector('#lame').innerText")
        check(f'{which} lame mode shows the dates', 'Feb 5' in txt)
        wide = await pg.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        check(f'{which} lame mode has no sideways scroll', not wide)
        live = await pg.evaluate("!document.querySelector('#world').classList.contains('hidden') && getComputedStyle(document.querySelector('#world')).display!=='none'")
        check(f'{which} lame mode has the live world behind it', live)
        await pg.screenshot(path=str(OUT / f'{which}-lame.png'), full_page=True, timeout=120000)
        check(f'{which} no script errors', not errs, '; '.join(errs[:3]))
        await b.close()

async def main():
    for w in (sys.argv[1:] or ['d', 'm']):
        await run(w)
    bad = [r for r in results if not r[1]]
    print(f'\n{len(results)-len(bad)} passed, {len(bad)} failed')
    sys.exit(1 if bad else 0)

asyncio.run(main())
