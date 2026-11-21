"""Public-state UI walkthroughs. Uses the existing agent, never secret labels."""
import argparse
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game.logic import ExhaustiveAgent,CRIMINAL,INNOCENT,UNKNOWN
from game.puzzles import DEMO_PROOFS


def run(base_url='http://127.0.0.1:5000'):
    Path('tmp/qa').mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1366,'height':768},device_scale_factor=1)
        errors,public_responses=[],[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def inspect(response):
            if '/api/' not in response.url or response.status!=200:return
            data=response.json()
            state=data.get('state',data) if isinstance(data,dict) else None
            if state and 'layout' in state:
                assert 'solution' not in state and 'initial' not in state
                assert len(state['clues'])==len(state['known'])
                assert all(c['owner'] in state['known'] for c in state['clues'])
                assert all(set(person)=={'id','row','column','name','profession'} for person in state['layout'])
                public_responses.append(response.url)
        page.on('response',inspect)
        def current():return page.request.get(base_url+'/api/state').json()
        def shot(name):page.screenshot(path=f'tmp/qa/scope41-{name}.png',full_page=True,animations='disabled')
        def go_cases():
            if page.locator('#play-screen').is_visible():page.locator('#choose-case').click()
            elif page.locator('#home-screen').is_visible():page.locator('#start').click()
            expect(page.locator('#cases-screen')).to_be_visible()
        def load(pid):
            go_cases();page.locator(f'[data-puzzle="{pid}"]').click();page.locator('#load').click()
            expect(page.locator('#play-screen')).to_be_visible()
            expect(page.locator('#notice-code')).to_have_text('LOADED')
        def choose(cell):
            if page.locator('#judgment').is_visible():page.locator('#close-judgment').click()
            page.locator(f'[data-cell="{cell}"]').click()
            expect(page.locator('#judgment')).to_be_visible()
        def verdict(cell,status,code):
            choose(cell)
            button='#criminal' if status==CRIMINAL else '#innocent'
            with page.expect_response('**/api/verdict'):page.locator(button).click()
            expect(page.locator('#notice-code')).to_have_text(code)
            if code!='ACCEPTED':expect(page.locator(button)).to_be_focused()
            return button
        page.goto(base_url)
        expect(page.locator('#home-screen')).to_be_visible()
        expect(page.locator('#continue')).to_be_hidden()
        expect(page.locator('.forest-scene')).to_have_attribute('src','/static/scenes/gridwolf-village-night.webp')
        shot('home')
        for pid,proof in DEMO_PROOFS.items():
            load(pid)
            initial=current()
            public=dict(layout=initial['layout'],known=initial['known'],clues=initial['clues'])
            inference=ExhaustiveAgent().classify(public)
            unknown=next(c for c,s in inference.statuses.items() if s==UNKNOWN)
            forced,status=next((c,s) for c,s in inference.statuses.items() if s!=UNKNOWN)
            verdict(unknown,CRIMINAL,'NOT_PROVABLE');assert current()==initial
            verdict(forced,INNOCENT if status==CRIMINAL else CRIMINAL,'CONTRADICTED');assert current()==initial
            expect(page.locator('#clear-clue')).to_be_hidden()
            if page.locator('#judgment').is_visible():page.locator('#close-judgment').click()
            # First easy steps are selected manually from the published walkthrough.
            for cell,status in proof['prefix']:verdict(cell,status,'ACCEPTED')
            if page.locator('#judgment').is_visible():page.locator('#close-judgment').click()
            page.locator('#hint').click();expect(page.locator('#notice-code')).to_have_text('HINT')
            expect(page.locator('.hinted')).to_have_count(0)
            page.locator('#hint').click();expect(page.locator('.hinted')).to_have_count(2)
            assert set(page.locator('.hinted').evaluate_all('(es)=>es.map(e=>e.dataset.clue)'))==set(proof['clue_ids'])
            snapshot=current()
            page.evaluate('window.testCard=document.querySelector(".card")')
            geometry=page.locator('#board').bounding_box()
            for cid in proof['clue_ids']:
                page.locator(f'[data-clue="{cid}"]').click()
                clue=next(c for c in snapshot['clues'] if c['id']==cid)
                assert set(page.locator('.highlight').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))==set(clue['cells'])
                assert page.evaluate('window.testCard===document.querySelector(".card")')
                assert page.locator('#board').bounding_box()==geometry
                expect(page.locator('#clear-clue')).to_be_visible()
            assert not page.locator('.oath-number,.book-icon,.ledger-help,.ledger-key').count()
            assert 'Be Vietnam Pro' in page.locator('.testimony .logic').first.evaluate('(e)=>getComputedStyle(e).fontFamily')
            highlight=page.locator('.card.highlight').first
            expect(highlight).to_have_css('border-top-color','rgb(207, 223, 213)')
            shot(pid+'-spotlight')
            page.locator('#clear-clue').click();expect(page.locator('.highlight')).to_have_count(0)
            cid=proof['clue_ids'][0]
            page.locator(f'[data-clue="{cid}"]').click();page.keyboard.press('Escape')
            expect(page.locator('.highlight')).to_have_count(0)
            page.locator(f'[data-clue="{cid}"]').click();page.locator(f'[data-clue="{cid}"]').click()
            expect(page.locator('.highlight')).to_have_count(0)
            page.locator(f'[data-clue="{cid}"]').click();page.locator('.map-note').click()
            expect(page.locator('.highlight')).to_have_count(0)
            verdict(proof['target'],proof['status'],'ACCEPTED')
            progressed=current()
            page.locator('#choose-case').click();expect(page.locator('#cases-screen')).to_be_visible()
            assert current()==progressed
            page.locator('#back-to-game').click();expect(page.locator('#play-screen')).to_be_visible()
            page.reload();expect(page.locator('.revealed')).to_have_count(progressed['progress'])
            page.locator('#auto').click();expect(page.locator('#restart')).to_be_disabled()
            expect(page.locator('#complete-dialog')).to_be_visible(timeout=40000)
            expect(page.locator('.revealed')).to_have_count(initial['total'])
            final=current()
            assert int(page.locator('#wolf-count').inner_text())==sum(s==CRIMINAL for s in final['known'].values())
            page.locator('#review-board').click()
            expect(page.locator('#complete-dialog')).to_be_hidden()
            page.locator('#trace-toggle').click();expect(page.locator('#trace-drawer')).to_be_visible()
            expect(page.locator('#trace li')).to_have_count(initial['total']-len(initial['known']))
            page.keyboard.press('Escape')
            if initial['size']>=4:
                assert page.locator('.ledger').evaluate('(e)=>e.scrollHeight>e.clientHeight')
            page.locator('#show-summary').click();page.locator('#complete-restart').click()
            expect(page.locator('.revealed')).to_have_count(len(initial['known']))
            assert current()==initial
            print('UI case PASS:',pid,flush=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        shot('mobile')
        page.locator('#hint').click();expect(page.locator('#notice-code')).to_have_text('HINT')
        page.emulate_media(reduced_motion='reduce')
        page.locator('[data-clue="clue-A1"]').click()
        assert page.locator('.card.highlight').first.evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
        assert not errors,errors
        print(f'Browser PASS: four original cases, manual proof checkpoints, real Verdict/Hint/Auto Solve, exact bright spotlight, flat ledger, restart/navigation, mobile/reduced motion; {len(public_responses)} public responses; no JS errors.')
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:5000')
    run(parser.parse_args().url)
