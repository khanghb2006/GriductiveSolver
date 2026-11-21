"""Targeted desktop fit, exact spotlight and last-row judgment checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run(base='http://127.0.0.1:5000'):
    Path('tmp/qa').mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1366,'height':768},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base)
        page.locator('#start').click()
        expect(page.locator('#cases-screen')).to_be_visible()
        def load(pid):
            if not page.locator('#cases-screen').is_visible():
                page.locator('#choose-case').click()
            page.locator(f'[data-puzzle="{pid}"]').click()
            page.locator('#load').click()
            expect(page.locator('#play-screen')).to_be_visible()
            expect(page.locator('#notice-code')).to_have_text('LOADED')
            page.locator('#play-screen').evaluate('(e)=>Promise.all(e.getAnimations().map(a=>a.finished.catch(()=>{})))')
        def shot(name):
            page.screenshot(path=f'tmp/qa/{name}.png',animations='disabled',full_page=True)
        def lit():
            return set(page.locator('.card.highlight').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))
        for width,height in [(1366,768),(1440,900)]:
            page.set_viewport_size({'width':width,'height':height})
            for size in (3,4,5):
                load(f'village-{size}')
                metrics=page.locator('.board-scroll').evaluate('(e)=>({client:e.clientHeight,scroll:e.scrollHeight,top:e.scrollTop})')
                assert metrics['scroll']<=metrics['client']+1, (width,size,metrics)
                assert metrics['top']==0
                assert page.evaluate('devicePixelRatio')==1
                for column in 'ABCDE'[:size]:
                    card=page.locator(f'[data-cell="{column}{size}"]')
                    box=card.bounding_box()
                    assert box['y']>=0 and box['y']+box['height']<=height-8, (size,box)
                    assert card.evaluate('(e)=>[...e.querySelectorAll("strong,.job,.label,.coord,img")].every(x=>{const r=x.getBoundingClientRect(),b=e.getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom+1&&r.left>=b.left&&r.right<=b.right+1})')
                last=f'{"ABCDE"[size-1]}{size}'
                page.locator(f'[data-cell="{last}"]').click()
                expect(page.locator('#judgment')).to_be_visible()
                if size==5:
                    expect(page.locator('#judgment')).to_have_attribute('data-placement','above')
                panel=page.locator('#judgment').bounding_box()
                assert panel['y']>=0 and panel['y']+panel['height']<=height-8
                page.locator('#innocent').click()
                expect(page.locator('#notice-code')).to_have_text('NOT_PROVABLE')
                page.locator('#close-judgment').click()
                if size in (4,5): shot(f'fit-{size}x{size}-{width}x{height}')
        load('village-3')
        # No node replacement, geometry changes or guessed membership on spotlight.
        page.evaluate('window.originalCard=document.querySelector("[data-cell=B1]")')
        before=page.locator('#board').bounding_box()
        page.locator('[data-clue="clue-A1"]').click(); assert lit()=={'C1'}
        page.locator('[data-clue="clue-A2"]').click(); assert lit()=={'B1','B2'}
        assert page.evaluate('window.originalCard===document.querySelector("[data-cell=B1]")')
        assert page.locator('#board').bounding_box()==before
        expect(page.locator('[data-clue="clue-A2"]')).to_have_attribute('aria-pressed','true')
        page.locator('[data-cell="B2"]').click()
        expect(page.locator('#criminal')).to_be_enabled()
        assert lit()=={'B1','B2'}
        page.locator('#close-judgment').click()
        shot('fit-spotlight')
        page.locator('[data-clue="clue-A2"]').click(); assert not lit()
        page.locator('[data-clue="clue-A1"]').click();page.keyboard.press('Escape');assert not lit()
        page.locator('[data-clue="clue-A2"]').click()
        page.locator('.map-note').click();assert not lit()
        # Prove the entire prefix via the real API, then judge E5 through the UI.
        load('village-5')
        while True:
            current=page.request.get(base+'/api/state').json()
            if current['progress']==24: break
            result=page.request.post(base+'/api/auto-step',data={}).json()
            assert result['code']=='ACCEPTED'
        assert 'E5' not in current['known']
        page.reload();expect(page.locator('.revealed')).to_have_count(24)
        page.locator('[data-cell="E5"]').click()
        expect(page.locator('#judgment')).to_have_attribute('data-placement','above')
        page.locator('#innocent').click()
        expect(page.locator('#complete-dialog')).to_be_visible()
        expect(page.locator('.revealed')).to_have_count(25)
        page.locator('#review-board').click()
        assert page.locator('.ledger').evaluate('(e)=>e.scrollHeight>e.clientHeight')
        page.locator('.ledger').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        assert page.locator('.ledger').evaluate('(e)=>e.scrollTop')>0
        assert page.locator('.board-scroll').evaluate('(e)=>e.scrollTop')==0
        shot('fit-long-ledger')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('.board-scroll').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
        shot('fit-mobile')
        page.set_viewport_size({'width':1100,'height':540})
        assert page.locator('.board-scroll').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
        assert page.evaluate('document.documentElement.scrollHeight>innerHeight')
        assert not errors,errors
        print('PASS: all rows at 1366x768/1440x900 and zoom 100%; no board Y-scroll; last-row popover + real E5 verdict; exact stable spotlight/toggle/Escape/blank; independent long ledger; mobile and short-window natural scrolling.')
        browser.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:5000')
    run(parser.parse_args().url)
