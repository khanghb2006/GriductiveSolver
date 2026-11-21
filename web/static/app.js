async function boot() {
  // Public views also upgrade a page cached by an already-running Flask server.
  const response = await fetch('/static/views.html');
  if (!response.ok) throw new Error('Không tải được giao diện. Vui lòng tải lại trang.');
  const view = new DOMParser().parseFromString(await response.text(), 'text/html');
  document.body.replaceChildren(...view.body.childNodes);
  document.title = 'Gridwolf';
  document.querySelector('link[rel="icon"]')?.setAttribute('href','/static/logo.svg');
const $ = id => document.getElementById(id);
const labels = {CRIMINAL: '◆ Sói', INNOCENT: '☀ Dân làng'};
let state, puzzles = [], chosenCase = null, route = 'home';
let selected = null, activeClue = null, hintIds = [], busy = false, auto = false, runId = 0;
let completionShown = false, feedback = {code: '', message: 'Chỉ phán khi bằng chứng đã đủ.'};
let toastTimer,moonSweepTimer,goldPulseTimer;
let paintedClue=null;
const motion = matchMedia('(prefers-reduced-motion: reduce)');
const watchers = [...document.querySelectorAll('.watcher')];
const watcherTimers = new Map();
function syncWatchers() {
  watcherTimers.forEach(clearTimeout); watcherTimers.clear();
  watchers.forEach(w => { w.onanimationend=null; w.classList.remove('is-awake'); w.getAnimations({subtree:true}).forEach(a=>a.cancel()); });
  if (motion.matches || document.hidden) return;
  watchers.forEach(w => scheduleWatcher(w, Math.random()*7000));
}
function scheduleWatcher(w, delay) {
  watcherTimers.set(w,setTimeout(()=>{
    if (motion.matches || document.hidden) return;
    w.style.setProperty('--visit-time',`${6500+Math.random()*6500}ms`);
    w.style.setProperty('--blink-at',`${900+Math.random()*2500}ms`);
    w.classList.add('is-awake');
    w.onanimationend=event=>{
      if (event.target !== w) return;
      w.onanimationend=null;
      w.classList.remove('is-awake');
      if (!motion.matches && !document.hidden) scheduleWatcher(w,4000+Math.random()*17000);
    };
  },delay));
}
motion.addEventListener('change',syncWatchers);
document.addEventListener('visibilitychange',syncWatchers);
syncWatchers();
const nfc = value => String(value ?? '').normalize('NFC');
function element(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = nfc(text);
  return e;
}
function uiText(text) { return nfc(text).replaceAll('Đồng phạm', 'Sói').replaceAll('Vô can', 'Dân làng'); }
async function request(path, body) {
  const response = await fetch('/api/' + path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error('Không thể thực hiện yêu cầu. Vui lòng thử lại.');
  return response.json();
}
function tone(code) {
  if (code === 'NOT_PROVABLE') return 'amber';
  return ['CONTRADICTED', 'DATA_ERROR', 'CONNECTION_ERROR'].includes(code) ? 'error' : '';
}
function notice(code, message) {
  $('notice-code').textContent = code; $('message').textContent = uiText(message);
  $('notice').className = 'notice is-visible ' + tone(code);
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>$('notice').classList.remove('is-visible'),code==='HINT'?7000:4500);
}
function canResume() { return state && !state.completed && state.history.length > 0; }
function navigate(next) {
  if (busy || auto) return;
  if (location.hash === '#' + next) showRoute(); else location.hash = next;
}
function showRoute(focusHeading = true) {
  if (!state) return;
  const previousRoute = route;
  const next = location.hash.slice(1);
  route = ['home', 'cases', 'play'].includes(next) ? next : 'home';
  // Browser Back may leave the timed loop; navigation never calls Load.
  if (route !== 'play' && auto) stopAuto();
  for (const screen of ['home', 'cases', 'play']) $(screen + '-screen').hidden = route !== screen;
  if (route !== previousRoute && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const screen = $(route + '-screen');
    screen.classList.remove('route-enter');
    void screen.offsetWidth;
    screen.classList.add('route-enter');
  }
  document.body.dataset.screen = route;
  $('continue').hidden = !canResume(); $('resume-description').hidden = !canResume();
  $('resume-description').textContent = nfc(`${state.title} · ${state.progress}/${state.total} đã xác định`);
  $('back-to-game').hidden = !state;
  if (route === 'cases') renderCases();
  if (route === 'play') { render(); maybeComplete(); }
  if (focusHeading && !$('complete-dialog').open) {
    $(route === 'home' ? 'home-title' : route === 'cases' ? 'cases-title' : 'map-title').focus({preventScroll: true});
    window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  }
  controls();
}
function controls() {
  if (!state) return;
  for (const id of ['load', 'restart', 'hint', 'auto', 'complete-restart', 'complete-choose', 'start', 'continue', 'back-to-game']) $(id).disabled = busy || auto;
  $('load').disabled ||= !chosenCase;
  $('auto').disabled ||= state.completed; $('hint').disabled ||= state.completed;
  const can = selected && !state.known[selected] && !busy && !auto;
  $('criminal').disabled = !can; $('innocent').disabled = !can;
  $('close-judgment').disabled = busy;
  $('stop').hidden = !auto; $('stop').disabled = busy;
  $('choose-case').setAttribute('aria-disabled', String(busy || auto));
  document.querySelectorAll('.card,.testimony,.case-card,.case-variant').forEach(e => e.disabled = busy || auto);
  $('clear-clue').disabled = busy || auto || !activeClue;
  $('clear-clue').hidden = !activeClue;
  $('judgment').hidden = route !== 'play' || !selected || !!state.known[selected] || auto;
  document.body.classList.toggle('has-selection', !$('judgment').hidden);
}
function renderCases() {
  const list = $('case-list'), entry=document.querySelector('.case-entry');
  entry.remove(); list.replaceChildren();
  const families = [...new Set(puzzles.map(p=>p.size))].map(size=>puzzles.filter(p=>p.size===size));
  families.forEach((family, i) => {
    const p=family.find(p=>p.id===chosenCase)||family[0];
    const selectedFamily=family.some(p=>p.id===chosenCase);
    const wrapper=element('div','case-family'+(selectedFamily?' chosen':''));
    const button = element('button', 'case-card' + (p.id === chosenCase ? ' chosen' : ''));
    button.dataset.puzzle = p.id; button.setAttribute('aria-pressed', String(p.id === chosenCase));
    button.append(element('span','case-index',`${String(i+1).padStart(2,'0')} / Hồ sơ đêm`));
    const preview=element('span','case-preview'); preview.style.setProperty('--preview-size',p.size);
    preview.setAttribute('aria-hidden','true');
    for(let n=0;n<p.size*p.size;n++) preview.append(element('span','preview-cell'+(n%7===0 || n===p.size+1?' lit':'')));
    button.append(preview, element('strong', '', p.title), element('span', 'case-size', `${p.size} × ${p.size} · ${p.size * p.size} người`));
    if (p.id === state.puzzle_id) button.append(element('span', 'case-progress', `${state.progress}/${state.total} đã xác định${state.completed ? ' · Hoàn tất' : ''}`));
    button.onclick = () => {
      selectCase(p.id);
    };
    wrapper.append(button);
    family.filter(other=>other.id!==p.id).forEach(other=>{
      const alternative=element('button','case-variant',`Hồ sơ khác: ${other.title}`);
      alternative.dataset.puzzle=other.id;
      alternative.onclick=()=>selectCase(other.id);
      wrapper.append(alternative);
    });
    if(selectedFamily) wrapper.append(entry);
    list.append(wrapper);
  });
  if(!entry.isConnected) list.after(entry);
  const p = puzzles.find(p => p.id === chosenCase);
  $('case-selection').textContent = p ? 'Hồ sơ đã chọn' : 'Chọn một hồ sơ';
  $('case-description').textContent = p ? 'Mở từ đầu khi vào làng.' : 'Chọn hồ sơ để bắt đầu.';
}
function selectCase(id) {
  if(busy || auto || id===chosenCase) return;
  const update=()=>{
    chosenCase=id;
    renderCases();
    controls();
    document.querySelector(`[data-puzzle="${id}"]`)?.focus({preventScroll:true});
  };
  // Blend the picker snapshots so moving the entry controls does not jump.
  if(!motion.matches && document.startViewTransition) document.startViewTransition(update);
  else update();
}
// cells is the exact public region resolved by the engine. Never parse clue prose.
function clueParts(c) {
  const group = (c.cells || []).join(' · ');
  if (c.type === 'FACT') return {before: '', group, after: ` là ${c.status === 'CRIMINAL' ? 'Sói' : 'Dân làng'}.`};
  if (c.type === 'SAME') return {before: '', group, after: ': hai người có cùng trạng thái.'};
  if (c.type === 'DIFFERENT') return {before: '', group, after: ': một Sói và một Dân làng.'};
  const prefix = {EXACTLY: 'Đúng', AT_LEAST: 'Ít nhất', AT_MOST: 'Nhiều nhất'}[c.type];
  return prefix ? {before: `${prefix} ${c.k} Sói trong nhóm: `, group, after: '.'} : null;
}
function savedFocus() {
  const e = document.activeElement;
  if (e?.dataset.cell) return `[data-cell="${e.dataset.cell}"]`;
  if (e?.dataset.clue) return `[data-clue="${e.dataset.clue}"]`;
  return null;
}
function render(previous) {
  const focus = savedFocus();
  const area = document.querySelector('.board-scroll');
  const boardScroll = {top:area.scrollTop,left:area.scrollLeft};
  $('map-title').textContent = nfc(state.title); $('progress').textContent = `${state.progress} / ${state.total} đã xác định`;
  $('meter').value = state.progress; $('meter').max = state.total;
  const clue = state.clues.find(c => c.id === activeClue), lit = new Set(clue?.cells || []);
  const reference = clue?.region?.kind === 'NEIGHBORS' ? clue.region.cell : null;
  const board = $('board'); board.className = `board size-${state.size}${clue ? ' spotlight' : ''}`; board.replaceChildren();
  board.style.setProperty('--columns', state.size);
  state.layout.forEach(person => {
    const status = state.known[person.id], fresh = status && previous && !previous.known[person.id];
    const card = element('button', 'card' + (status ? ' revealed ' + status : '') +
      (selected === person.id ? ' selected' : '') + (lit.has(person.id) ? ' highlight' : '') +
      (reference === person.id ? ' reference' : '') + (fresh ? ' fresh' : ''));
    card.dataset.cell = person.id; card.setAttribute('aria-pressed', String(selected === person.id));
    card.setAttribute('aria-label', nfc(`${person.id}, ${person.name}, ${person.profession}, ${status ? labels[status] : 'Chưa phán'}`));
    if (!status) card.setAttribute('aria-controls', 'judgment');
    const roof = element('div', 'card-top');
    roof.append(element('span', 'coord', person.id));
    const image = element('img', 'avatar');
    image.src = '/static/characters/' + (status === 'CRIMINAL' ? 'wolf' : status === 'INNOCENT' ? 'villager' : 'unknown') + '.svg';
    image.alt = '';
    roof.append(image);
    card.append(roof, element('strong', '', person.name), element('span', 'job', person.profession), element('span', 'label', status ? labels[status] : 'Chưa rõ'));
    card.onclick = () => {
      selected = person.id; feedback = {code: '', message: 'Chỉ phán khi bằng chứng đã đủ.'};
      if (status) { const id = state.clues.find(c => c.owner === person.id)?.id; activeClue = activeClue === id ? null : id; }
      paintSpotlight(); paintSelection(true); card.focus({preventScroll: true});
    };
    board.append(card);
  });
  area.scrollTo({...boardScroll,behavior:'instant'});
  const ledger = $('clues'); ledger.replaceChildren();
  state.clues.forEach(c => {
    const owner = state.layout.find(p => p.id === c.owner), fresh = previous && !previous.known[c.owner];
    const button = element('button', 'testimony' + (c.id === activeClue ? ' active' : '') +
      (hintIds.includes(c.id) ? ' hinted' : '') + (fresh ? ' new-testimony' : ''));
    button.dataset.clue = c.id; button.setAttribute('aria-pressed', String(c.id === activeClue));
    button.append(element('span', 'witness', `${c.owner} · ${owner.name} · ${c.heading}`));
    const logic = element('span', 'logic'), parts = clueParts(c);
    if (parts) {
      logic.append(document.createTextNode(nfc(parts.before)), element('span', 'clue-region', parts.group), document.createTextNode(nfc(parts.after)));
      if (c.region?.kind === 'NEIGHBORS') logic.append(element('span', 'clue-reference', ` Tâm tham chiếu: ${c.region.cell}.`));
    } else logic.textContent = uiText(c.text);
    button.append(logic);
    button.onclick = () => {
      activeClue = activeClue === c.id ? null : c.id;
      paintSpotlight(); button.focus({preventScroll: true});
    };
    ledger.append(button);
  });
  paintSelection();
  $('trace').replaceChildren();
  for (const step of state.history) $('trace').append(element('li', '', `${step.cell} · ${labels[step.status]} · Đã chứng minh`));
  $('trace-count').textContent = `(${state.history.length} bước)`; $('show-summary').hidden = !state.completed;
  controls();
  if (focus) document.querySelector(focus)?.focus({preventScroll: true});
  positionJudgment();
  updateBoardScrollHint();
  if (previous && state.history.length > previous.history.length) {
    const added = state.clues.find(c => !previous.known[c.owner]);
    if (added && route === 'play' && !matchMedia('(max-width: 760px)').matches) {
      const entry = document.querySelector(`[data-clue="${added.id}"]`), panel = document.querySelector('.ledger');
      if (entry) panel.scrollBy({top:Math.max(0,entry.getBoundingClientRect().bottom-panel.getBoundingClientRect().bottom+20),
        behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    }
    const last = state.history.at(-1);
    const card = last && document.querySelector(`[data-cell="${last.cell}"]`);
    if (card && !matchMedia('(max-width: 760px)').matches) {
      const box = area.getBoundingClientRect(), r = card.getBoundingClientRect();
      const top = r.top < box.top ? r.top-box.top-8 : r.bottom > box.bottom ? r.bottom-box.bottom+8 : 0;
      area.scrollBy({top,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    }
  }
}
function paintSpotlight() {
  const clue=state.clues.find(c=>c.id===activeClue);
  const cells=new Set(clue?.cells||[]);
  const reference=clue?.region?.kind==='NEIGHBORS'?clue.region.cell:null;
  const changed=(clue?.id||null)!==paintedClue;
  if(changed) stopMoonSweep();
  $('board').classList.toggle('spotlight',!!clue);
  document.querySelectorAll('.card').forEach(card=>{
    card.classList.toggle('highlight',cells.has(card.dataset.cell));
    card.classList.toggle('reference',reference===card.dataset.cell);
  });
  document.querySelectorAll('.testimony').forEach(button=>{
    const active=button.dataset.clue===activeClue;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',String(active));
  });
  $('clear-clue').disabled=busy||auto||!clue;
  $('clear-clue').hidden=!clue;
  paintedClue=clue?.id||null;
  if(changed&&clue&&!motion.matches){
    // Forty milliseconds normally; cap dense regions at 320ms in total.
    const step=Math.min(40,140/Math.max(1,cells.size-1));
    void $('board').offsetWidth;
    [...cells].forEach((cell,index)=>{
      const card=document.querySelector(`[data-cell="${cell}"]`);
      if(!card)return;
      card.style.setProperty('--moon-delay',`${index*step}ms`);
      card.classList.add('moon-sweep');
    });
    moonSweepTimer=setTimeout(stopMoonSweep,350);
  }
}
function stopMoonSweep(){
  clearTimeout(moonSweepTimer);
  document.querySelectorAll('.moon-sweep').forEach(card=>{
    card.classList.remove('moon-sweep');card.style.removeProperty('--moon-delay');
  });
}
function stopGoldPulse(){
  clearTimeout(goldPulseTimer);
  document.querySelectorAll('.gold-pulse').forEach(card=>card.classList.remove('gold-pulse'));
}
motion.addEventListener('change',()=>{if(motion.matches){stopMoonSweep();stopGoldPulse();}});
function paintSelection(pulse=false) {
  document.querySelectorAll('.card').forEach(card=>{
    card.classList.toggle('selected',card.dataset.cell===selected);
    card.setAttribute('aria-pressed',String(card.dataset.cell===selected));
  });
  const person=state.layout.find(p=>p.id===selected);
  $('selected').textContent=person?nfc(`${person.id} · ${person.name}`):'';
  $('selected-note').textContent=person?nfc(person.profession):'';
  $('local-feedback').textContent=uiText(feedback.message);
  $('local-feedback').className='local-feedback '+tone(feedback.code);
  controls(); positionJudgment();
  if(pulse){
    stopGoldPulse();
    if(selected&&!state.known[selected]&&!motion.matches){
      const card=document.querySelector(`[data-cell="${selected}"]`);
      if(card){
        void card.offsetWidth;card.classList.add('gold-pulse');
        goldPulseTimer=setTimeout(stopGoldPulse,430);
      }
    }
  }
}
function positionJudgment() {
  const panel = $('judgment');
  if (panel.hidden || matchMedia('(max-width: 760px)').matches) return;
  const card = document.querySelector(`[data-cell="${selected}"]`); if (!card) return;
  const r = card.getBoundingClientRect(), box = panel.getBoundingClientRect();
  panel.style.left = `${Math.max(12, Math.min(innerWidth - box.width - 12, r.left + r.width / 2 - box.width / 2))}px`;
  const below = r.bottom + 8;
  const fitsBelow=below+box.height<=innerHeight-12;
  panel.dataset.placement=fitsBelow?'below':'above';
  panel.style.top = `${fitsBelow ? below : Math.max(12, Math.min(innerHeight-box.height-12,r.top-box.height-8))}px`;
}
function updateBoardScrollHint() {
  const area = document.querySelector('.board-scroll');
  const horizontal = area.scrollWidth > area.clientWidth + 1;
  const vertical = area.scrollHeight > area.clientHeight + 1;
  $('board-scroll-hint').hidden = !horizontal && !vertical;
  $('board-scroll-hint').textContent = horizontal
    ? 'Kéo ngang trong bàn để xem đủ các cột. Có thể dùng phím trái/phải khi chọn vùng bàn.'
    : 'Cuộn trong bàn để xem các hàng còn lại.';
}
function clearSelection() {
  const old = selected; selected = null; stopGoldPulse(); paintSelection();
  if (old) document.querySelector(`[data-cell="${old}"]`)?.focus({preventScroll: true});
}
function maybeComplete() {
  if (route !== 'play' || !state.completed || completionShown) return;
  completionShown = true;
  $('wolf-count').textContent = Object.values(state.known).filter(s => s === 'CRIMINAL').length;
  $('villager-count').textContent = Object.values(state.known).filter(s => s === 'INNOCENT').length;
  $('complete-case').textContent = nfc(`${state.title} · ${state.total}/${state.total} đã xác định`);
  $('complete-dialog').showModal();
}
function stopAuto() { auto = false; runId++; controls(); }
async function act(action, data = {}) {
  if (busy || (auto && action !== 'auto-step')) return;
  const trigger = document.activeElement?.id;
  busy = true; controls();
  try {
    const result = await request(action, data), previous = state;
    if (!result.state) throw new Error('Phản hồi thiếu trạng thái ván. Vui lòng tải lại trang.');
    state = result.state;
    if (['LOADED', 'RESTARTED', 'ACCEPTED'].includes(result.code)) {
      hintIds = [];
      if (result.code !== 'ACCEPTED') {
        selected = null; activeClue = null; completionShown = false;
        paintedClue=null;stopMoonSweep();stopGoldPulse();
        feedback = {code: '', message: 'Chỉ phán khi bằng chứng đã đủ.'};
      }
    }
    if (result.code === 'HINT') hintIds = result.clue_ids || [];
    if (action === 'verdict') feedback = {code: result.code, message: result.message};
    if (action === 'auto-step' && result.code === 'ACCEPTED') selected = state.history.at(-1)?.cell || null;
    notice(result.code, result.message); render(previous);
    if (state.completed) {
      auto = false; notice('COMPLETE', 'Làng đã yên. Tất cả đã được xác định bằng chứng cứ.'); maybeComplete();
    }
    return result;
  } catch (error) {
    notice('CONNECTION_ERROR', error.message); feedback = {code: 'CONNECTION_ERROR', message: error.message};
    $('local-feedback').textContent = nfc(error.message); $('local-feedback').className = 'local-feedback error';
    if (route !== 'play') { $('app-error').hidden = false; $('app-error').textContent = nfc(error.message); }
    stopAuto();
  } finally {
    busy = false; controls();
    if (action === 'verdict' && selected && !state.known[selected] && trigger) $(trigger)?.focus({preventScroll: true});
    else if (action === 'verdict' && selected && state.known[selected] && !$('complete-dialog').open) document.querySelector(`[data-cell="${selected}"]`)?.focus({preventScroll: true});
  }
}
$('start').onclick = () => navigate('cases'); $('continue').onclick = () => navigate('play');
$('back-to-game').onclick = () => navigate('play');
$('choose-case').onclick = event => { if (busy || auto) event.preventDefault(); };
$('load').onclick = async () => {
  if (!chosenCase) return;
  const result = await act('load', {puzzle_id: chosenCase});
  if (result?.code === 'LOADED') navigate('play');
};
$('restart').onclick = () => act('restart');
$('hint').onclick = async () => {
  const result = await act('hint');
  if (result?.clue_ids?.length) {
    const clue = document.querySelector(`[data-clue="${result.clue_ids[0]}"]`);
    clue?.focus({preventScroll: true}); clue?.scrollIntoView({block: 'nearest', behavior: 'instant'});
  }
};
$('criminal').onclick = () => act('verdict', {cell: selected, status: 'CRIMINAL'});
$('innocent').onclick = () => act('verdict', {cell: selected, status: 'INNOCENT'});
$('clear-clue').onclick = () => { activeClue = null; paintSpotlight(); };
$('close-judgment').onclick = clearSelection;
$('stop').onclick = () => { stopAuto(); notice('STOPPED', 'Tự giải đã dừng. Bạn có thể tiếp tục phán.'); };
$('auto').onclick = async () => {
  if (busy || auto || state.completed) return;
  auto = true; const token = ++runId; controls();
  while (auto && token === runId && route === 'play') {
    const result = await act('auto-step');
    if (!result || result.code !== 'ACCEPTED' || state.completed) break;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  if (token === runId) { auto = false; controls(); }
};
$('how-to').onclick = event => { event.preventDefault(); $('guide-dialog').showModal(); };
$('view-rules').onclick = $('how-to').onclick;
$('trace-toggle').onclick=()=>$('trace-drawer').showModal();
$('close-trace').onclick=()=>$('trace-drawer').close();
for (const id of ['close-guide', 'understood']) $(id).onclick = () => $('guide-dialog').close();
for (const id of ['close-complete', 'review-board']) $(id).onclick = () => { $('complete-dialog').close(); $('show-summary').focus({preventScroll: true}); };
$('show-summary').onclick = () => { completionShown = false; maybeComplete(); };
$('complete-choose').onclick = () => { $('complete-dialog').close(); navigate('cases'); };
$('complete-restart').onclick = async () => { $('complete-dialog').close(); await act('restart'); $('map-title').focus({preventScroll: true}); };
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || $('guide-dialog').open || $('complete-dialog').open || $('trace-drawer').open || busy || auto) return;
  if (activeClue) { activeClue = null; paintSpotlight(); } else if (selected) clearSelection();
});
document.addEventListener('click',event=>{
  if(route!=='play'||!activeClue||busy||auto) return;
  if(event.target.closest('button,a,dialog,.judgment')) return;
  activeClue=null; paintSpotlight();
});
window.addEventListener('hashchange', () => showRoute());
window.addEventListener('resize', () => { positionJudgment(); updateBoardScrollHint(); });
window.addEventListener('scroll', positionJudgment, {passive: true});
document.querySelector('.board-scroll').addEventListener('scroll', positionJudgment, {passive: true});
async function init() {
  try {
    [puzzles, state] = await Promise.all([request('puzzles'), request('state')]);
    chosenCase = state.puzzle_id || puzzles[0]?.id; render(); showRoute(false);
  } catch (error) {
    $('app-error').hidden = false;
    $('app-error').textContent = nfc('Không tải được ván. Kiểm tra server rồi tải lại trang. ' + error.message);
  }
}
init();

}
boot().catch(error => {
  const message = document.createElement('p');
  message.setAttribute('role', 'alert');
  message.textContent = error.message;
  document.body.replaceChildren(message);
});
