"""UI-only checks for exact rules copy, shared scene, moon sweep and gold focus."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

RULES=[
('Đọc bằng chứng:','Mọi lời thề đã mở đều đúng, kể cả lời của Sói, còn tên và nghề chỉ giúp nhận diện nhân vật.'),
('Soi vùng:','Bấm lời thề để làm sáng các ô được nhắc tới trên bàn, với cột ký hiệu bằng chữ, hàng bằng số và ô kề tính cả đường chéo nhưng bỏ ô trung tâm.'),
('Chọn người và phán:','Chọn Kết tội cho Sói hoặc Minh oan cho Dân làng khi bằng chứng đã đủ, vì đoán đúng vẫn bị từ chối nếu chưa thể chứng minh.'),
('Mở thêm lời thề:','Mỗi phán quyết hợp lệ lật thẻ và mở một manh mối mới để bạn suy luận tiếp.'),
('Dùng gợi ý:','Bấm Hint để xem gợi ý cách suy luận, rồi bấm lần nữa để đánh dấu lời thề liên quan.'),
('Tự động giải:','Auto Solve dùng cùng luật chứng minh để lật từng thẻ.'),
]


def run(base='http://127.0.0.1:5000'):
    Path('tmp/qa').mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        b=p.chromium.launch(channel='chrome',headless=True)
        page=b.new_page(viewport={'width':1366,'height':768},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def shot(name):page.screenshot(path=f'tmp/qa/moon-{name}.png',full_page=True,animations='disabled')
        page.goto(base);expect(page.locator('#home-screen')).to_be_visible()
        page.locator('#how-to').click()
        expect(page.locator('#guide-title')).to_have_text('Đọc lời thề - Tìm sự thật')
        expect(page.locator('.instructions li')).to_have_count(6)
        for i,(label,body) in enumerate(RULES):
            item=page.locator('.instructions li').nth(i)
            expect(item.locator('strong')).to_have_text(label)
            expect(item).to_have_text(label+' '+body)
            assert body.count('.')==1
        expect(page.locator('.session-note')).to_have_text('Tiến độ chỉ được giữ trong phiên server hiện tại.')
        shot('rules')
        page.locator('#understood').click();expect(page.locator('#guide-dialog')).to_be_hidden()
        page.locator('#view-rules').click();page.locator('#close-guide').click()
        page.locator('#view-rules').click();page.keyboard.press('Escape')
        expect(page.locator('#guide-dialog')).to_be_hidden()
        shot('home')
        page.locator('#start').click();expect(page.locator('#cases-screen')).to_be_visible()
        page.locator('#load').click();expect(page.locator('#play-screen')).to_be_visible()
        page.locator('#play-screen').evaluate('(e)=>Promise.all(e.getAnimations().map(a=>a.finished.catch(()=>{})))')
        assert page.locator('.forest-scene').get_attribute('src')==page.locator('.gameplay-scene').get_attribute('src')
        before=page.locator('#board').bounding_box()
        pair=page.locator('[data-clue="clue-A2"]')
        pair.click()
        assert set(page.locator('.moon-sweep').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))=={'B1','B2'}
        delays=page.locator('.moon-sweep').evaluate_all('(es)=>es.map(e=>parseFloat(e.style.getPropertyValue("--moon-delay")))')
        assert delays==[0,40]
        assert max(delays)+180<350
        assert page.locator('#board').bounding_box()==before
        page.locator('[data-cell="B1"]').click()
        expect(page.locator('#criminal')).to_be_enabled()
        expect(page.locator('[data-cell="B1"]')).to_have_class(__import__('re').compile('.*gold-pulse.*'))
        assert set(page.locator('.highlight').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))=={'B1','B2'}
        card=page.locator('[data-cell="B1"]')
        assert card.evaluate('(e)=>getComputedStyle(e).outlineColor')!=card.evaluate('(e)=>getComputedStyle(e).borderTopColor')
        assert card.evaluate('(e)=>getComputedStyle(e,"::before").pointerEvents')=='none'
        assert card.evaluate('(e)=>getComputedStyle(e,"::after").pointerEvents')=='none'
        shot('silver-and-gold')
        page.locator('[data-clue="clue-A1"]').click()
        assert set(page.locator('.highlight').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))=={'C1'}
        assert set(page.locator('.moon-sweep').evaluate_all('(es)=>es.map(e=>e.dataset.cell)'))=={'C1'}
        page.keyboard.press('Escape');expect(page.locator('.highlight')).to_have_count(0)
        expect(page.locator('.moon-sweep')).to_have_count(0)
        page.locator('#close-judgment').click()
        pair.click();pair.click();expect(page.locator('.highlight')).to_have_count(0)
        pair.click();page.locator('#clear-clue').click();expect(page.locator('.highlight')).to_have_count(0)
        page.emulate_media(reduced_motion='reduce')
        pair.click();expect(page.locator('.moon-sweep')).to_have_count(0)
        page.locator('[data-cell="B2"]').click();expect(page.locator('.gold-pulse')).to_have_count(0)
        expect(page.locator('.card.highlight.selected')).to_have_count(1)
        assert page.locator('.card.highlight.selected').evaluate('(e)=>getComputedStyle(e,"::before").animationName')=='none'
        page.locator('#close-judgment').click();page.keyboard.press('Escape')
        page.emulate_media(reduced_motion='no-preference')
        for width,height in [(1366,768),(1440,900),(390,844),(320,760)]:
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            for selector in ['.brand','#choose-case','[data-cell="A1"]']:
                box=page.locator(selector).bounding_box();assert box['x']>=0,(width,selector,box)
            if width>=1000:
                for pid,size in [('village-4',4),('village-5',5)]:
                    page.locator('#choose-case').click();page.locator(f'[data-puzzle="{pid}"]').click();page.locator('#load').click()
                    expect(page.locator('.card')).to_have_count(size*size)
                    last=page.locator(f'[data-cell="A{size}"]').bounding_box()
                    assert last['y']+last['height']<height
                    assert page.locator('.board-scroll').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
                    shot(f'{size}x{size}-{width}')
            else:shot(f'mobile-{width}')
        assert not errors,errors
        print('Moon UI PASS: exact six rules/colons; close/Understood/Escape; shared scene; exact B1/B2 sweep (0/40ms); silver+gold coexist; stable geometry; toggle/clear/Escape; reduced motion; desktop fit and no left clipping; mobile; no JS errors.')
        b.close()


if __name__=='__main__':run()
