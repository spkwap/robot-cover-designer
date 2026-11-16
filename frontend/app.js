'use strict';
const $ = (s, r = document) => r.querySelector(s);
const S = { lang: localStorage.getItem('lang') || 'pl', meta: null, project: null, res: null, page: 'dashboard', lib: 'materials',
  viz: { view: 'front', cover: true, robot: true, byModule: true, seams: true, closures: true, labels: true, yaw: .6, pitch: .35 }, sel: { piece: 1 } };
const T = (a, b) => S.lang === 'pl' ? a : b;
const tx = o => o && typeof o === 'object' && 'pl' in o ? (o[S.lang] || o.pl) : (o ?? '');
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (v, d = 1) => v == null ? '–' : (typeof v === 'number' ? (+v.toFixed(d)).toString() : v);

async function api(path, opt = {}) {
  const isF = opt.body instanceof FormData;
  const r = await fetch('/api' + path, { ...opt, headers: opt.body && !isF ? { 'Content-Type': 'application/json' } : {}, body: opt.body && !isF ? JSON.stringify(opt.body) : opt.body });
  if (!r.ok) { let m = await r.text(); try { const j = JSON.parse(m); m = typeof j.detail === 'string' ? j.detail : (j.detail?.message || m); } catch (e) { } throw new Error(m); }
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
}
const getP = (o, p) => p.split('.').reduce((a, k) => a == null ? a : a[k], o);
function setP(o, p, v) { const ks = p.split('.'); let a = o; ks.slice(0, -1).forEach((k, i) => { if (a[k] == null) a[k] = /^\d+$/.test(ks[i + 1]) ? [] : {}; a = a[k]; }); a[ks.at(-1)] = v; }

const PAGES = [['dashboard', 'Dashboard', 'Dashboard'], ['new', 'Nowy projekt', 'New Project'], ['robot', 'Konfiguracja robota', 'Robot Configuration'], ['environment', 'Analiza środowiska', 'Environment Analysis'],
  ['material', 'Dobór materiału', 'Material Selection'], ['design', 'Konstrukcja pokrowca', 'Cover Design'], ['pattern', 'Generator wykrojów', 'Pattern Generator'],
  ['sewing', 'Technologia szycia', 'Sewing Configuration'], ['bom', 'Lista materiałów', 'Bill of Materials'], ['docs', 'Dokumentacja produkcyjna', 'Production Documentation'], ['library', 'Baza danych', 'Data library']];
const NEEDS = { robot: 'robot', environment: 'environment', material: 'material', design: 'design', pattern: 'pattern', sewing: 'sewing', bom: 'bom', docs: 'docs' };

/* ---------- save / compute ---------- */
let saveT = null, dirtyFlag = false;
function dirty() { dirtyFlag = true; clearTimeout(saveT); saveT = setTimeout(flush, 600); S.res = null; }
async function flush() {
  clearTimeout(saveT); if (!dirtyFlag || !S.project) return; dirtyFlag = false; const p = S.project;
  await api('/projects/' + p.id, { method: 'PUT', body: { name: p.name, robot: p.robot, environment: p.environment, requirements: p.requirements } });
}
async function compute(force) {
  await flush(); if (S.res && !force) return S.res;
  S.res = await api('/projects/' + S.project.id + '/run', { method: 'POST' });
  const fresh = await api('/projects/' + S.project.id); S.project.progress = fresh.progress; S.project.status = fresh.status; S.project.validation_summary = fresh.validation_summary; S.project.files = fresh.files;
  return S.res;
}
async function openProject(id) { S.project = await api('/projects/' + id); S.res = null; go('robot'); }

/* ---------- shell ---------- */
function side() {
  const pr = S.project?.progress || {};
  $('#side').innerHTML = `<h1>Robot Cover Designer</h1>` + PAGES.map(([k, pl, en]) => {
    const st = NEEDS[k] ? `<span class="dot ${pr[NEEDS[k]] ? 'ok' : ''}"></span>` : '<span class="dot" style="visibility:hidden"></span>';
    const dis = NEEDS[k] && !S.project;
    return `<a data-go="${k}" class="${S.page === k ? 'on' : ''}" style="${dis ? 'opacity:.4' : ''}">${st}${T(pl, en)}</a>`;
  }).join('') + `<div class="sep"></div>` + (S.project ? `<div style="padding:4px 10px;font-size:12px"><b>${esc(S.project.name)}</b><br>${statusBadge()}</div>` : '') +
    `<div class="sep"></div><div class="lang" style="padding:0 10px"><button data-lang="pl" class="${S.lang === 'pl' ? 'on' : ''}">PL</button><button data-lang="en" class="${S.lang === 'en' ? 'on' : ''}">EN</button></div>`;
}
function statusBadge() {
  const v = S.project?.validation_summary;
  let s = S.project?.status === 'approved' ? `<span class="badge b-green">${T('ZATWIERDZONY', 'APPROVED')}</span>` : `<span class="badge b-grey">${T('roboczy', 'draft')}</span>`;
  if (v) s += ` <span class="badge b-red">${v.red}</span><span class="badge b-yellow">${v.yellow}</span><span class="badge b-green">${v.green}</span>`;
  return s;
}
async function go(page) {
  await flush(); S.page = page; side();
  const need = NEEDS[page];
  if (['dashboard', 'new', 'library'].includes(page) || !S.project) { if (need && !S.project) { S.page = 'dashboard'; page = 'dashboard'; side(); } }
  $('#main').innerHTML = `<div class="empty">…</div>`;
  try { $('#main').innerHTML = await PAGE[page](); } catch (e) { $('#main').innerHTML = `<div class="alert r">${esc(e.message)}</div>`; }
  if (AFTER[page]) AFTER[page]();
  window.scrollTo(0, 0);
}
const head = (pl, en, sub) => `<h2>${T(...[pl, en])}</h2>${sub ? `<div class="sub">${sub}</div>` : ''}`;
const badge = (st) => `<span class="badge b-${st}">${{ green: T('ZIELONY', 'GREEN'), yellow: T('ŻÓŁTY', 'YELLOW'), red: T('CZERWONY', 'RED') }[st]}</span>`;
const conf = c => `<span class="badge ${c === 'verified' ? 'b-green' : c === 'unverified' ? 'b-red' : 'b-yellow'}">${c === 'verified' ? T('zweryfikowane', 'verified') : c === 'partial' ? T('częściowo z dokumentu', 'partly from document') : c === 'typical' ? T('typowe (niepotwierdzone)', 'typical (unconfirmed)') : T('niezweryfikowane', 'unverified')}</span>`;
const rate = (r) => r == null ? `<span class="rate rn">${T('nieznana', 'unknown')}</span>` : `<span class="rate r${r}">${tx(S.meta.ratings[r])}</span>`;

/* ---------- field helpers ---------- */
const val = (p) => { const v = getP(S.project, p); return v == null ? '' : v; };
const inp = (p, o = {}) => `<input data-path="${p}" type="${o.type || 'text'}" ${o.step ? `step="${o.step}"` : ''} value="${esc(val(p))}" ${o.ph ? `placeholder="${esc(o.ph)}"` : ''} ${o.dis ? 'disabled' : ''} ${o.list ? `list="${o.list}"` : ''} ${o.rr ? 'data-rr=1' : ''}>`;
const num = (p, o = {}) => inp(p, { ...o, type: 'number', step: o.step || 'any' });
const sel = (p, opts, o = {}) => `<select data-path="${p}" ${o.rr ? 'data-rr=1' : ''}>${opts.map(([v, l]) => `<option value="${v}" ${String(val(p)) === String(v) ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
const chk = (p, o = {}) => `<input type="checkbox" data-path="${p}" ${getP(S.project, p) ? 'checked' : ''} ${o.dis ? 'disabled' : ''}>`;
const fld = (label, html) => `<label class="f">${label}${html}</label>`;
const cfld = (label, p) => `<label class="f" style="flex-direction:row;align-items:center;gap:6px;color:var(--ink)">${chk(p)} ${label}</label>`;

document.addEventListener('change', async e => {
  const el = e.target; if (!el.dataset?.path || !S.project) return;
  let v = el.type === 'checkbox' ? el.checked : el.type === 'number' ? (el.value === '' ? null : +el.value) : el.value;
  if (el.tagName === 'SELECT' && (v === 'true' || v === 'false')) v = v === 'true';
  if (el.dataset.path === 'requirements.material_override' && v === '') v = null;
  setP(S.project, el.dataset.path, v); dirty();
  if (el.dataset.path === 'name') side();
  if (el.dataset.rr) go(S.page);
});
document.addEventListener('click', async e => {
  const a = e.target.closest('[data-go],[data-lang],[data-act]'); if (!a) return;
  if (a.dataset.go) return go(a.dataset.go);
  if (a.dataset.lang) { S.lang = a.dataset.lang; localStorage.setItem('lang', S.lang); document.documentElement.lang = S.lang; side(); return go(S.page); }
  const fn = ACT[a.dataset.act]; if (fn) { try { await fn(a); } catch (err) { alert(err.message); } }
});

/* ---------- pages ---------- */
const PAGE = {}, AFTER = {}, ACT = {};

PAGE.dashboard = async () => {
  const list = await api('/projects');
  return head('Dashboard — projekty', 'Dashboard - projects', T('Lista zapisanych projektów pokrowców.', 'List of saved cover projects.')) +
    `<div class="card"><div class="row"><button class="pri" data-go="new">+ ${T('Nowy projekt', 'New project')}</button><button data-act="example">${T('Otwórz projekt demonstracyjny', 'Open demo project')}</button></div></div>` +
    (list.length ? `<div class="card tw"><table><tr><th>${T('Nazwa', 'Name')}</th><th>Robot</th><th>${T('Status', 'Status')}</th><th>${T('Postęp', 'Progress')}</th><th>${T('Zmieniono', 'Updated')}</th><th></th></tr>` +
      list.map(p => { const pr = p.progress || {}, n = Object.values(pr).filter(Boolean).length, tot = 8; return `<tr><td><a href="#" data-act="open" data-id="${p.id}">${esc(p.name)}</a></td><td>${esc(p.robot)}</td><td>${p.status === 'approved' ? `<span class="badge b-green">${T('zatwierdzony', 'approved')}</span>` : `<span class="badge b-grey">${T('roboczy', 'draft')}</span>`}</td>
      <td><div class="bar"><i style="width:${n / tot * 100}%"></i></div></td><td class="mut">${new Date(p.updated * 1000).toLocaleString()}</td><td><button data-act="open" data-id="${p.id}">${T('Otwórz', 'Open')}</button> <button class="dng" data-act="del" data-id="${p.id}">✕</button></td></tr>`; }).join('') + '</table></div>' : `<div class="empty">${T('Brak projektów.', 'No projects yet.')}</div>`) +
    `<div class="alert i">${T('Dane materiałowe w bazie mają status „typowe” (rodzina materiałowa) — status ZIELONY w walidacji wymaga potwierdzenia kartą TDS w module „Baza danych”.', 'Catalogue data have "typical" status (material family) - GREEN validation status requires TDS confirmation in the "Data library" module.')}</div>`;
};
ACT.open = a => openProject(a.dataset.id);
ACT.del = async a => { if (confirm(T('Usunąć projekt?', 'Delete project?'))) { await api('/projects/' + a.dataset.id, { method: 'DELETE' }); if (S.project?.id === a.dataset.id) S.project = null; go('dashboard'); } };
ACT.example = async () => { S.project = await api('/projects', { method: 'POST', body: { example: true } }); S.res = null; go('robot'); };

PAGE.new = async () => head('Nowy projekt', 'New project') + `<div class="card"><div class="grid">${fld(T('Nazwa projektu', 'Project name'), '<input id="np" value="">')}</div>
  <p><label><input type="checkbox" id="npx"> ${T('Zacznij od projektu demonstracyjnego (fikcyjny robot, przykładowe wymiary)', 'Start from the demo project (fictional robot, illustrative dimensions)')}</label></p><button class="pri" data-act="create">${T('Utwórz projekt', 'Create project')}</button></div>`;
ACT.create = async () => { S.project = await api('/projects', { method: 'POST', body: { name: $('#np').value || T('Nowy pokrowiec', 'New cover'), example: $('#npx').checked } }); S.res = null; go('robot'); };

/* ----- robot ----- */
const SEGCOLS = [['name', 'text', T('Segment', 'Segment')], ['shape', 'shape', T('Kształt', 'Shape')], ['length', 'num', T('Dł. [mm]', 'Len [mm]')], ['d1', 'num', 'Ø1 [mm]'], ['d2', 'num', 'Ø2 [mm]'], ['width', 'num', T('Szer. [mm]', 'Width [mm]')], ['depth', 'num', T('Głęb. [mm]', 'Depth [mm]')],
  ['neutral_angle', 'num', T('Kąt neutr. [°]', 'Neutral ang [°]')], ['cover', 'chk', T('Osłaniać', 'Cover')], ['joint_after.type', 'joint', T('Przegub za', 'Joint after')], ['joint_after.axis', 'num', T('Oś nr', 'Axis')], ['joint_after.min', 'num', T('Min [°]', 'Min [°]')], ['joint_after.max', 'num', T('Max [°]', 'Max [°]')],
  ['hot_c', 'num', T('T pow. [°C]', 'Surf T [°C]')], ['protrusion_h', 'num', T('Wystaje [mm]', 'Protr [mm]')], ['cooling_vent', 'chk', T('Chłodzenie', 'Cooling')], ['service', 'chk', T('Serwis', 'Service')], ['closed_end', 'chk', T('Zamk. koniec', 'Closed end')]];
PAGE.robot = async () => {
  const p = S.project, r = p.robot; r.segments = r.segments || [];
  const mfrs = ['FANUC', 'KUKA', 'ABB', 'Yaskawa', 'Universal Robots', 'Kawasaki', 'Stäubli'];
  const segRows = r.segments.map((s, i) => `<tr><td>${i + 1}</td>` + SEGCOLS.map(([k, t]) => {
    const path = `robot.segments.${i}.${k}`; let h;
    const dis = (k === 'd1' && s.shape === 'box') || (k === 'd2' && s.shape !== 'frustum') || ((k === 'width' || k === 'depth') && s.shape !== 'box') || (k.startsWith('joint_after.') && k !== 'joint_after.type' && !(s.joint_after && ['bend', 'twist'].includes(s.joint_after.type)));
    if (t === 'text') h = inp(path, { dis: 0 }); else if (t === 'num') h = num(path, { dis });
    else if (t === 'chk') h = chk(path); else if (t === 'shape') h = sel(path, [['cylinder', T('walec', 'cylinder')], ['frustum', T('stożek', 'frustum')], ['box', T('prostopadłościan', 'box')]], { rr: 1 });
    else h = sel(path, [['none', T('sztywny', 'rigid')], ['bend', T('zginany', 'bending')], ['twist', T('obrotowy', 'twist')]], { rr: 1 });
    return `<td>${h}</td>`; }).join('') + `<td style="white-space:nowrap"><button data-act="segup" data-i="${i}">↑</button><button data-act="segdn" data-i="${i}">↓</button><button class="dng" data-act="segdel" data-i="${i}">✕</button></td></tr>`).join('');
  const ops = []; r.segments.forEach((s, i) => (s.openings || []).forEach((o, j) => ops.push([i, j, o])));
  const opRows = ops.map(([i, j]) => { const b = `robot.segments.${i}.openings.${j}.`; return `<tr><td>${esc(r.segments[i].name)}</td><td>${inp(b + 'name')}</td><td>${sel(b + 'type', [['cable', T('przepust kablowy', 'cable pass-through')], ['keepout', T('strefa niezakryta / dostęp', 'keep-out / access')]])}</td><td>${sel(b + 'kind', [['round', T('okrągły', 'round')], ['rect', T('prostokątny', 'rect')]])}</td><td>${num(b + 'pos_mm')}</td><td>${num(b + 'angle_deg')}</td><td>${num(b + 'size1')}</td><td>${num(b + 'size2')}</td><td><button class="dng" data-act="opdel" data-i="${i}" data-j="${j}">✕</button></td></tr>`; }).join('');
  const files = (p.files || []).map(f => `<div>${f.kind === 'photo' ? `<a href="/api/projects/${p.id}/files/${f.name}" target="_blank"><img src="/api/projects/${p.id}/files/${f.name}" style="height:70px;border-radius:4px;vertical-align:middle"></a> ` : ''}<b>${esc(f.name)}</b> <span class="mut">(${f.kind}, ${(f.size / 1024).toFixed(0)} kB)</span>${f.bbox ? ` — bbox [mm]: <span class="mono">${f.bbox.size.map(v => v.toFixed(0)).join(' × ')}</span> (${T('porównaj z sumą długości segmentów — dane z modelu, nie są użyte automatycznie', 'compare with the segment lengths - model data, not used automatically')})` : ''}${f.error ? `<span class="badge b-yellow">${esc(f.error)}</span>` : ''}</div>`).join('');
  const preview = VIZ.view2d('front', r.segments.filter(s => +s.length > 0 && (+s.d1 > 0 || +s.width > 0)), null, { robot: true, cover: false, labels: true });
  return head('Konfiguracja robota', 'Robot configuration', T('Etapy 1–2: dane robota i geometria. Wymiary wprowadzasz dla każdego segmentu osobno — system nie zakłada prostej bryły i niczego nie uzupełnia „z głowy”.', 'Stages 1-2: robot data and geometry. Enter dimensions per segment - the system does not assume a simple solid and fills in nothing by guesswork.')) +
    `<div class="card"><datalist id="mf">${mfrs.map(m => `<option>${m}</option>`).join('')}</datalist><div class="grid">
    ${fld(T('Nazwa projektu', 'Project name'), inp('name'))}${fld(T('Producent', 'Manufacturer'), inp('robot.manufacturer', { list: 'mf' }))}${fld(T('Model (dokładny)', 'Model (exact)'), inp('robot.model'))}${fld(T('Wersja / generacja', 'Version / generation'), inp('robot.version'))}
    ${fld(T('Typ robota', 'Robot type'), sel('robot.type', [['articulated', T('przegubowy', 'articulated')], ['cobot', T('współpracujący (cobot)', 'collaborative (cobot)')], ['scara', 'SCARA'], ['delta', 'delta'], ['cartesian', T('kartezjański', 'cartesian')], ['manipulator', T('manipulator', 'manipulator')], ['other', T('inny', 'other')]]))}
    ${fld(T('Liczba osi', 'Number of axes'), num('robot.axes'))}${fld(T('Zastosowanie robota', 'Robot application'), inp('robot.application'))}${fld(T('Lokalizacja i montaż', 'Location and mounting'), inp('robot.mounting'))}</div></div>
    <div class="card"><h3 style="margin-top:0">${T('Wyszukiwanie modelu w bazie', 'Look up a model in the database')}</h3><div class="row"><input id="rq" placeholder="${T('np. UR5e, FANUC, KUKA…', 'e.g. UR5e, FANUC, KUKA...')}" style="max-width:300px"><button data-act="robsearch">${T('Szukaj', 'Search')}</button></div><div id="rres"></div>
    <div class="alert i">${T('Baza zawiera tylko dane katalogowe (zasięg, udźwig, osie) oznaczone jako niezweryfikowane i BEZ wymiarów segmentów. Pobieranie danych z internetu nie jest zaimplementowane — wymiary wprowadź ręcznie wg dokumentacji producenta lub zaimportuj model.', 'The database holds catalogue-level data only (reach, payload, axes) marked unverified and WITHOUT segment dimensions. Online retrieval from manufacturer sites is not implemented - enter dimensions manually from the manufacturer documentation or import a model.')}</div></div>
    <div class="card"><div class="row"><h3 style="margin:0">${T('Segmenty robota (od podstawy do końcówki)', 'Robot segments (base to tool)')}</h3><span class="sp"></span><button data-act="segadd">+ ${T('Segment', 'Segment')}</button><button data-act="segtpl">${T('Szablon wg liczby osi', 'Template from axis count')}</button></div>
    <p class="mut" style="margin:4px 0 8px">${T('Przegub „za” segmentem łączy go z następnym. Zakres min/max w stopniach względem pozycji neutralnej (0°), w której opisano geometrię; „kąt neutralny” obraca oś segmentu względem poprzedniego (0° = kontynuacja, −90° = zgięcie poziomo).', 'A joint "after" a segment connects it to the next one. Min/max range in degrees relative to the neutral pose (0°) in which the geometry is described; the "neutral angle" rotates the segment axis relative to the previous one (0° = continues, -90° = bent horizontal).')}</p>
    <div class="tw"><table><tr><th>#</th>${SEGCOLS.map(c => `<th>${c[2]}</th>`).join('')}<th></th></tr>${segRows}</table></div></div>
    <div class="card"><div class="row"><h3 style="margin:0">${T('Przepusty kablowe i strefy niezakryte', 'Cable pass-throughs and keep-out zones')}</h3><span class="sp"></span><button data-act="opadd">+ ${T('Otwór', 'Opening')}</button></div>
    ${ops.length ? `<div class="tw"><table><tr><th>${T('Segment', 'Segment')}</th><th>${T('Nazwa', 'Name')}</th><th>${T('Rodzaj', 'Purpose')}</th><th>${T('Kształt', 'Shape')}</th><th>${T('Położenie wzdłuż [mm]', 'Position along [mm]')}</th><th>${T('Kąt od zamka [°]', 'Angle from closure [°]')}</th><th>${T('Wymiar 1 [mm]', 'Size 1 [mm]')}</th><th>${T('Wymiar 2 [mm]', 'Size 2 [mm]')}</th><th></th></tr>${opRows}</table></div>` : `<div class="mut">${T('Brak. Dodaj, jeśli przewody/złącza wychodzą przez pokrowiec lub sensor/element bezpieczeństwa wymaga otworu.', 'None. Add if cables/connectors pass through the cover or a sensor/safety element needs an opening.')}</div>`}</div>
    <div class="card"><h3 style="margin-top:0">${T('Zdjęcia, rysunki, modele', 'Photos, drawings, models')}</h3><div class="row"><label class="f">${T('Zdjęcie robota', 'Robot photo')}<input type="file" accept="image/*" data-up="photo"></label><label class="f">${T('Model 3D / rysunek (STL, OBJ, DXF; STEP — tylko zapis)', '3D model / drawing (STL, OBJ, DXF; STEP - stored only)')}<input type="file" data-up="model"></label></div>${files}</div>
    <div class="card"><div class="row"><h3 style="margin:0">${T('Podgląd schematyczny (bez pokrowca)', 'Schematic preview (no cover)')}</h3><span class="sp"></span><button class="pri" data-act="geocheck">${T('Sprawdź geometrię i ruch', 'Check geometry and motion')}</button></div><div id="geores"></div><div class="viz" style="max-width:520px;margin-top:8px">${preview}<span class="wm">${T('SCHEMAT — nie model CAD', 'SCHEMATIC - not a CAD model')}</span></div></div>`;
};
AFTER.robot = () => document.querySelectorAll('[data-up]').forEach(el => el.onchange = async () => { const f = el.files[0]; if (!f) return; const fd = new FormData(); fd.append('file', f); await flush(); await api(`/projects/${S.project.id}/upload?kind=${el.dataset.up}`, { method: 'POST', body: fd }); S.project = await api('/projects/' + S.project.id); go('robot'); });
const newSeg = () => ({ name: '', shape: 'cylinder', length: null, d1: null, cover: true, neutral_angle: 0, joint_after: { type: 'none' } });
ACT.segadd = () => { S.project.robot.segments.push(newSeg()); dirty(); go('robot'); };
ACT.segdel = a => { S.project.robot.segments.splice(+a.dataset.i, 1); dirty(); go('robot'); };
ACT.segup = a => { const s = S.project.robot.segments, i = +a.dataset.i; if (i > 0) { [s[i - 1], s[i]] = [s[i], s[i - 1]]; dirty(); go('robot'); } };
ACT.segdn = a => { const s = S.project.robot.segments, i = +a.dataset.i; if (i < s.length - 1) { [s[i + 1], s[i]] = [s[i], s[i + 1]]; dirty(); go('robot'); } };
ACT.segtpl = () => { const n = +S.project.robot.axes || 6; const names = ['Base', 'Turret', 'Lower arm', 'Upper arm', 'Wrist 1', 'Wrist 2', 'Flange']; if (S.project.robot.segments.length && !confirm(T('Zastąpić istniejące segmenty szablonem (puste wymiary)?', 'Replace existing segments with a template (empty dimensions)?'))) return;
  S.project.robot.segments = Array.from({ length: Math.min(n + 1, 7) }, (_, i) => ({ ...newSeg(), name: names[i] || 'Segment ' + (i + 1), joint_after: { type: i === 0 ? 'twist' : 'bend', axis: i + 1 } })); dirty(); go('robot'); };
ACT.opadd = () => { const s = S.project.robot.segments; if (!s.length) return alert(T('Najpierw dodaj segment.', 'Add a segment first.')); const i = +(prompt(T('Numer segmentu (1–' + s.length + ')', 'Segment number (1-' + s.length + ')'), '1') || 0) - 1; if (!s[i]) return; (s[i].openings ||= []).push({ name: '', type: 'cable', kind: 'round', pos_mm: 100, angle_deg: 90, size1: 40 }); dirty(); go('robot'); };
ACT.opdel = a => { S.project.robot.segments[+a.dataset.i].openings.splice(+a.dataset.j, 1); dirty(); go('robot'); };
ACT.robsearch = async () => { const l = await api('/robots?q=' + encodeURIComponent($('#rq').value)); $('#rres').innerHTML = `<div class="tw"><table>${l.map(r => `<tr><td>${esc(r.manufacturer)} <b>${esc(r.model)}</b></td><td>${r.type}, ${r.axes} ${T('osi', 'axes')}, ${T('zasięg', 'reach')} ${r.reach_mm} mm, ${T('udźwig', 'payload')} ${r.payload_kg} kg</td><td>${conf(r.confidence)}${r.verified_fields ? `<div class="mut" style="font-size:11px">${esc(r.verified_fields.join(', '))}</div>` : ''}</td><td><button data-act="robpick" data-id="${r.id}">${T('Użyj', 'Use')}</button></td></tr>`).join('') || `<tr><td>${T('Brak w bazie — wprowadź ręcznie.', 'Not in database - enter manually.')}</td></tr>`}</table></div>`; };
ACT.robpick = async a => { const l = await api('/robots'); const r = l.find(x => x.id === a.dataset.id); Object.assign(S.project.robot, { manufacturer: r.manufacturer, model: r.model, type: r.type, axes: r.axes, db_ref: r.id, reach_mm: r.reach_mm, payload_kg: r.payload_kg }); dirty(); go('robot'); };
ACT.geocheck = async () => { const res = await compute(true); const g = res.geometry; let h = '';
  if (g.errors.length) h = `<div class="alert r"><b>${T('Brakujące / błędne dane geometrii', 'Missing / invalid geometry data')}</b><ul>${g.errors.map(e => `<li>${esc(tx(e.text))}</li>`).join('')}</ul></div>`;
  else { const c = g.clearance; h = `<div class="alert ${c.gap != null && c.gap < 0 ? 'r' : 'g'}">${T('Geometria kompletna.', 'Geometry complete.')} ${c.gap != null ? T(`Min. odstęp osłon przy ruchu (model płaski): ${c.gap.toFixed(0)} mm (${c.pair?.join(' ↔ ')}).`, `Min. cover gap in motion (planar model): ${c.gap.toFixed(0)} mm (${c.pair?.join(' <-> ')}).`) : ''}<br>${T('Przeguby zginane wymagające sekcji harmonijkowych: ', 'Bending joints needing bellows: ')}${Object.values(g.joints.per_joint).filter(j => j.needs_bellows).length}</div>`; }
  $('#geores').innerHTML = h; side(); };

/* ----- environment ----- */
PAGE.environment = async () => {
  const env = S.project.environment; env.factors ||= {}; const M = S.meta;
  const groups = [['chem', T('A. Czynniki chemiczne', 'A. Chemical factors')], ['phys', T('B. Czynniki fizyczne', 'B. Physical factors')], ['thermal', T('C. Czynniki termiczne', 'C. Thermal factors')], ['atmos', T('D. Czynniki atmosferyczne', 'D. Atmospheric factors')], ['motion', T('E. Ruch robota', 'E. Robot motion')], ['special', T('F. Wymagania specjalne', 'F. Special requirements')]];
  const unknownCrit = M.factors.filter(f => f.critical && (env.factors[f.key]?.state || 'unknown') === 'unknown');
  const fsel = f => { const cur = env.factors[f.key] || {}; const v = cur.state === 'present' ? String(cur.level || 2) : (cur.state || 'unknown'); const lab = M.level_labels[f.kind];
    const opts = [['unknown', T('? nie wiem / do ustalenia', '? unknown / to be determined')], ['absent', T('nie występuje', 'absent')], ...(f.kind === 'bool' ? [['2', T('występuje', 'present')]] : [['1', tx(lab[0])], ['2', tx(lab[1])], ['3', tx(lab[2])]])];
    return `<select data-fk="${f.key}" style="${v === 'unknown' ? 'border-color:var(--y)' : ''}">${opts.map(([o, l]) => `<option value="${o}" ${o === v ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>`; };
  return head('Analiza środowiska pracy', 'Environment analysis', T('Etap 3. Brak zaznaczenia NIE oznacza braku czynnika — „nie wiem” pozostaje otwartym pytaniem i obniża status walidacji.', 'Stage 3. No selection does NOT mean the factor is absent - "unknown" stays an open question and lowers the validation status.')) +
    `<div class="card"><h3 style="margin-top:0">${T('Opis tekstowy → sugestie czynników', 'Free text -> suggested factors')}</h3><textarea id="atxt" placeholder="${T('np. Obróbka z emulsją chłodzącą, wióry stalowe, sporadyczne iskry, mycie ciśnieniowe raz w tygodniu…', 'e.g. Machining with cooling emulsion, steel chips, occasional sparks, weekly pressure washing...')}"></textarea>
    <div class="row" style="margin-top:6px"><button data-act="assist">${T('Analizuj tekst', 'Analyse text')}</button><span class="mut">${T('Analiza słownikowa (bez AI generatywnej): tylko sugestie, każdą potwierdzasz ręcznie; nie generuje żadnych wartości liczbowych.', 'Keyword analysis (no generative AI): suggestions only, each must be confirmed manually; it generates no numeric values.')}</span></div><div id="assres"></div></div>
    <div class="card"><h3 style="margin-top:0">${T('Parametry liczbowe', 'Numeric parameters')}</h3><div class="grid">
    ${fld(T('Temperatura minimalna [°C] *', 'Minimum temperature [°C] *'), num('environment.tmin_c'))}${fld(T('Temperatura maksymalna otoczenia [°C] *', 'Maximum ambient temperature [°C] *'), num('environment.tmax_c'))}
    ${fld(T('Temperatura powierzchni robota [°C]', 'Robot surface temperature [°C]'), num('environment.tsurface_c'))}${fld(T('Temp. gorących elementów w kontakcie [°C]', 'Hot contact temperature [°C]'), num('environment.hot_contact_c'))}
    ${fld(T('Temperatura szczytowa chwilowa [°C]', 'Short-term peak temperature [°C]'), num('environment.tpeak_c'))}${fld(T('Wilgotność względna [%]', 'Relative humidity [%]'), num('environment.humidity_pct'))}
    ${fld(T('Cykli ruchu na dobę', 'Motion cycles per day'), num('environment.cycles_per_day'))}${fld(T('Wymagania branżowe (np. spożywcza, farmacja)', 'Industry requirements (e.g. food, pharma)'), inp('environment.industry_compliance'))}
    ${fld(T('Rodzaj pyłu / uwagi', 'Dust type / notes'), inp('environment.notes'))}</div></div>
    <div class="alert ${unknownCrit.length ? '' : 'g'}" id="qbox"><b>${T('Pytania uzupełniające', 'Follow-up questions')}:</b> ${unknownCrit.length ? T(`${unknownCrit.length} istotnych czynników bez odpowiedzi: `, `${unknownCrit.length} critical factors unanswered: `) + unknownCrit.map(f => esc(tx(f.label))).join(', ') : T('wszystkie istotne czynniki rozstrzygnięte.', 'all critical factors resolved.')}</div>` +
    groups.map(([g, title]) => `<div class="card"><h3 style="margin-top:0">${title}</h3><div class="grid">${M.factors.filter(f => f.group === g).map(f => fld(`${esc(tx(f.label))}${f.critical ? ' <b style="color:var(--y)">*</b>' : ''}`, fsel(f))).join('')}</div></div>`).join('');
};
AFTER.environment = () => document.querySelectorAll('[data-fk]').forEach(el => el.onchange = () => { const v = el.value; S.project.environment.factors[el.dataset.fk] = v === 'unknown' ? { state: 'unknown' } : v === 'absent' ? { state: 'absent' } : { state: 'present', level: +v }; dirty(); el.style.borderColor = v === 'unknown' ? 'var(--y)' : ''; });
ACT.assist = async () => { const l = await api('/assist/environment', { method: 'POST', body: { text: $('#atxt').value } }); window._sug = l; $('#assres').innerHTML = l.length ? `<div class="tw"><table><tr><th>${T('Czynnik', 'Factor')}</th><th>${T('Poziom (1–3)', 'Level (1-3)')}</th><th>${T('Pewność', 'Confidence')}</th><th>${T('Fragment tekstu', 'Text evidence')}</th><th></th></tr>${l.map((s, i) => `<tr><td>${esc(tx(s.label))}</td><td>${s.level}</td><td>${s.confidence}</td><td class="mut">${esc(s.evidence)}</td><td><button data-act="sugapply" data-i="${i}">${T('Zastosuj', 'Apply')}</button></td></tr>`).join('')}</table></div>` : `<div class="mut">${T('Nic nie rozpoznano.', 'Nothing recognised.')}</div>`; };
ACT.sugapply = a => { const s = window._sug[+a.dataset.i]; S.project.environment.factors[s.key] = { state: 'present', level: s.level }; dirty(); go('environment'); };

/* ----- gating helper ----- */
async function need(stageKey) {
  const res = await compute(); const st = res.stage;
  const order = ['geometry', 'environment', 'construction', 'complete'];
  if (st === 'geometry') return [res, `<div class="alert r"><b>${T('Brak kompletnej geometrii', 'Geometry incomplete')}</b><ul>${res.geometry.errors.map(e => `<li>${esc(tx(e.text))}</li>`).join('')}</ul><button data-go="robot">${T('Przejdź do konfiguracji robota', 'Go to robot configuration')}</button></div>`];
  if (st === 'environment') return [res, `<div class="alert r"><b>${T('Brakujące dane środowiska', 'Missing environment data')}</b><ul>${res.environment.completeness.missing.map(e => `<li>${esc(tx(e.text))}</li>`).join('')}</ul><button data-go="environment">${T('Przejdź do analizy środowiska', 'Go to environment analysis')}</button></div>`];
  if (st === 'construction') return [res, `<div class="alert r"><b>${T('Konstrukcja niemożliwa', 'Construction impossible')}</b><ul>${res.construction.errors.map(e => `<li>${esc(tx(e.text))}</li>`).join('')}</ul></div>`];
  return [res, null];
}

/* ----- material ----- */
PAGE.material = async () => {
  const [res, err] = await need(); if (err) return head('Dobór materiału', 'Material selection') + err;
  const m = res.material, r = m.recommended, pack = res.environment.pack, e = r.effective; const mats = await api('/db/materials');
  const req = pack.requirements.map(q => `<tr><td>${esc(tx(q.type === 'chem' ? S.meta.chem[q.key] : S.meta.props[q.key] || { pl: q.key, en: q.key }))}</td><td>${q.type === 'test' || q.type === 'cert' ? T('dokument / próba', 'document / test') : rate(q.need)}</td><td class="mut">${q.reasons.map(x => esc(tx(x))).join('; ')}</td></tr>`).join('');
  return head('Dobór materiału', 'Material selection', T('Jeden rekomendowany materiał główny wynikający z reguł dopasowania (deterministycznie) — nie z oceny „ogólnej charakterystyki”.', 'One recommended main material from deterministic matching rules - not from a "general characteristics" impression.')) +
    m.warnings.map(w => `<div class="alert ${r.meets_all ? '' : 'r'}">${esc(tx(w))}</div>`).join('') +
    `<div class="card"><div class="row"><h3 style="margin:0">${T('Rekomendowany materiał', 'Recommended material')}: ${esc(tx(r.name))}</h3>${conf(r.confidence)}${r.meets_all ? `<span class="badge b-green">${T('spełnia wszystkie wymagania z bazy', 'meets all catalogue requirements')}</span>` : `<span class="badge b-red">${T('NIE spełnia wszystkich wymagań', 'does NOT meet all requirements')}</span>`}${r.requires_tests ? `<span class="badge b-yellow">${T('wymaga dodatkowych testów', 'additional tests required')}</span>` : ''}</div>
    <div class="grid" style="margin-top:10px">${[[T('Producent / produkt', 'Manufacturer / product'), r.product || T('— do wskazania wg TDS (przykłady dostawców: ', '- to be specified per TDS (supplier examples: ') + esc(r.example_suppliers) + ')'], [T('Gramatura', 'Weight'), `${r.gsm[0]}–${r.gsm[1]} g/m² (${T('typowo', 'typical')})`], [T('Grubość', 'Thickness'), `${r.thickness_mm[0]}–${r.thickness_mm[1]} mm`], [T('Skład', 'Composition'), esc(tx(r.composition))], [T('Powłoka', 'Coating'), esc(tx(r.coating))],
    [T('Zakres temperatur (ciągły)', 'Temperature range (continuous)'), `${r.tmin_c} … ${r.tmax_c} °C` + (r.tpeak_c ? ` (${T('chwilowo do', 'peak')} ${r.tpeak_c})` : '')], [T('Wytrzymałość na rozciąganie', 'Tensile strength'), r.tensile_n_50mm ? `${r.tensile_n_50mm[0]}–${r.tensile_n_50mm[1]} N/50 mm (${T('typowo', 'typical')})` : '–'],
    [T('Źródło dokumentacji', 'Documentation source'), esc(tx(r.source)) + (r.tds_url ? ` — <a href="${esc(r.tds_url)}" target="_blank">TDS</a>` : '')], [T('Data pozyskania danych', 'Data acquisition date'), r.source_date]].map(([k, v]) => `<div><div class="mut" style="font-size:11px">${k}</div>${v}</div>`).join('')}</div>
    <p><b>${T('Uzasadnienie', 'Justification')}:</b> ${esc(tx(r.justification))}</p><p><b>${T('Ograniczenia materiału', 'Material limitations')}:</b> ${esc(tx(r.limitations))}</p></div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(320px,1fr))"><div class="card"><h3 style="margin-top:0">${T('Odporność chemiczna', 'Chemical resistance')}</h3><table>${r.chemical.map(c => `<tr><td>${esc(tx(c.label))}</td><td>${rate(c.rating)}</td></tr>`).join('')}</table></div>
    <div class="card"><h3 style="margin-top:0">${T('Odporność mechaniczna i inne', 'Mechanical and other')}</h3><table>${r.mechanical.map(c => `<tr><td>${esc(tx(c.label))}</td><td>${rate(c.rating)}</td></tr>`).join('')}</table></div></div>
    <div class="card"><h3 style="margin-top:0">${T('Wymagania wyprowadzone ze środowiska', 'Requirements derived from the environment')}</h3><div class="tw"><table><tr><th>${T('Właściwość', 'Property')}</th><th>${T('Wymagane min.', 'Required min.')}</th><th>${T('Przyczyna', 'Reason')}</th></tr>${req}</table></div>
    <p class="mut">${T('Temperatura wymagana (ciągła)', 'Required continuous temperature')}: ${pack.tmin_req} … ${pack.tmax_req} °C (+10 K ${T('margines', 'margin')}). ${pack.critical_unresolved.length ? `<b>${pack.critical_unresolved.length} ${T('istotnych czynników nierozstrzygniętych', 'critical factors unresolved')}</b>` : ''}</p></div>
    <div class="card"><h3 style="margin-top:0">${T('Sprawdzenie wymagań vs materiał', 'Requirement vs material check')}</h3><div class="tw"><table><tr><th>${T('Wymaganie', 'Requirement')}</th><th>${T('Wymagane', 'Required')}</th><th>${T('Materiał', 'Material')}</th><th>${T('Wynik', 'Result')}</th></tr>${r.checks.map(c => { const isR = /^(chem|prop)/.test(c.req); const st = { fail: ['red', T('niespełnione', 'FAIL')], ok: ['green', 'OK'], ok_unverified: ['yellow', T('OK wg danych typowych', 'OK per typical data')], unknown: ['yellow', T('brak danych / ryzyko', 'no data / risk')], marginal: ['yellow', T('na granicy', 'marginal')], test: ['yellow', T('wymaga próby', 'needs test')] }[c.status]; return `<tr><td>${esc(tx(c.label))}</td><td>${c.need == null ? '' : isR ? rate(c.need) : fmt(c.need)}</td><td>${c.rating == null && isR ? rate(null) : isR ? rate(c.rating) : fmt(c.rating)}</td><td><span class="badge b-${st[0]}">${st[1]}</span></td></tr>`; }).join('')}</table></div></div>
    <div class="card"><h3 style="margin-top:0">${T('Dane potwierdzone przez dostawcę (z karty TDS)', 'Supplier-confirmed data (from the TDS)')}</h3><div class="grid">${fld(T('Konkretny produkt (producent + nazwa)', 'Specific product (manufacturer + name)'), inp('requirements.confirmed.product'))}${fld(T('Gramatura [g/m²]', 'Weight [g/m²]'), num('requirements.confirmed.gsm'))}${fld(T('Grubość [mm]', 'Thickness [mm]'), num('requirements.confirmed.thickness_mm', { step: '0.01' }))}${fld(T('Skurcz wzdłuż osnowy [%]', 'Warp shrinkage [%]'), num('requirements.confirmed.shrink_warp_pct'))}${fld(T('Skurcz wzdłuż wątku [%]', 'Weft shrinkage [%]'), num('requirements.confirmed.shrink_weft_pct'))}${fld('URL TDS', inp('requirements.confirmed.tds_url'))}
    ${fld(T('Materiał — wybór ręczny (nadpisanie)', 'Material - manual override'), sel('requirements.material_override', [['', T('automatycznie (rekomendacja)', 'automatic (recommendation)')], ...mats.filter(x => x.role === 'main').map(x => [x.id, tx(x.name)])]))}</div>
    <div class="row" style="margin-top:8px"><button class="pri" data-act="recalc">${T('Przelicz', 'Recalculate')}</button><span class="mut">${T('Wartości potwierdzone zastępują zakresy typowe w obliczeniach wykroju, szycia i masy. Podniesienie statusu materiału do „zweryfikowane” — w module Baza danych.', 'Confirmed values replace typical ranges in pattern, sewing and mass calculations. Raising the material status to "verified" - in the Data library module.')}</span></div></div>
    <details><summary>${T('Dlaczego nie inne materiały?', 'Why not other materials?')}</summary><div class="tw"><table>${m.rejected.map(x => `<tr><td>${esc(tx(x.name))}</td><td>${x.reasons.map(q => esc(tx(q.label))).join(', ')}</td></tr>`).join('')}</table></div></details>`;
};
ACT.recalc = async () => { await flush(); S.res = null; go(S.page); };

/* ----- design ----- */
function vizBlock(res) {
  const v = S.viz, segs = S.project.robot.segments.filter(s => +s.length > 0); const o = { robot: v.robot, cover: v.cover, byModule: v.byModule, seams: v.seams, closures: v.closures, labels: v.labels };
  const tabs = [['front', T('Przód', 'Front')], ['side', T('Bok', 'Side')], ['top', T('Góra', 'Top')], ['3d', '3D']];
  const body = v.view === '3d' ? VIZ.view3d(segs, res, o, v.yaw, v.pitch) : VIZ.view2d(v.view, segs, res, o);
  const tg = (k, l) => `<label style="margin-right:12px"><input type="checkbox" data-vz="${k}" ${v[k] ? 'checked' : ''}> ${l}</label>`;
  return `<div class="card"><div class="tabs">${tabs.map(([k, l]) => `<button data-act="vview" data-v="${k}" class="${v.view === k ? 'on' : ''}">${l}</button>`).join('')}</div>
  <div>${tg('robot', T('robot (bez pokrowca)', 'robot (no cover)'))}${tg('cover', T('pokrowiec', 'cover'))}${tg('byModule', T('kolory modułów', 'module colours'))}${tg('seams', T('szwy (czerwone)', 'seams (red)'))}${tg('closures', T('zapięcia (zielone/fiolet.)', 'closures (green/violet)'))}${tg('labels', T('etykiety', 'labels'))}</div>
  <div class="viz" id="vizbox" style="margin-top:8px">${body}<span class="wm">${T('WIZUALIZACJA SCHEMATYCZNA — nie jest modelem CAD ani projektem produkcyjnym', 'SCHEMATIC VISUALISATION - not a CAD model nor a production design')}</span></div>
  <div class="mut" style="margin-top:4px">${VIZ.legend(res)} ${v.view === '3d' ? '· ' + T('przeciągnij myszą, aby obrócić', 'drag to rotate') : ''}</div></div>`;
}
PAGE.design = async () => {
  const [res, err] = await need(); const R = 'requirements.';
  const form = `<div class="card"><h3 style="margin-top:0">${T('Wymagania dotyczące pokrowca (etap 4)', 'Cover requirements (stage 4)')}</h3><div class="grid">
    ${fld(T('Zakres', 'Scope'), sel(R + 'scope', [['full', T('cały robot', 'whole robot')], ['partial', T('wybrane segmenty (flaga „Osłaniać” w tabeli segmentów)', 'selected segments ("Cover" flag in the segment table)')]]))}
    ${fld(T('Szerokość beli materiału [mm]', 'Material roll width [mm]'), num(R + 'roll_width_mm'))}${fld(T('Liczba warstw', 'Number of layers'), sel(R + 'layers', [[1, T('1 (jednowarstwowy)', '1 (single layer)')], [2, T('2 (z wkładem termoizolacyjnym)', '2 (with thermal liner)')]]))}
    ${fld(T('Wysokość plis harmonijki [mm]', 'Bellows pleat height [mm]'), num(R + 'pleat_height_mm'))}${fld(T('Zdejmowanie [razy/miesiąc]', 'Removals [per month]'), num(R + 'removal_per_month'))}${fld(T('Oczekiwana żywotność [lata]', 'Expected lifetime [years]'), num(R + 'lifetime_years'))}
    ${fld(T('Maks. masa pokrowca [kg]', 'Max cover mass [kg]'), num(R + 'max_mass_kg'))}${fld(T('Kolor', 'Colour'), inp(R + 'color'))}${fld(T('Oznaczenia', 'Markings'), inp(R + 'marking'))}</div>
    <div class="row" style="margin-top:8px">${cfld(T('zdejmowany', 'removable'), R + 'removable')}${cfld(T('modułowy (inaczej jednoczęściowy)', 'modular (else one-piece)'), R + 'modular')}${cfld(T('zamki błyskawiczne', 'zippers'), R + 'zipper')}${cfld(T('rzepy', 'hook & loop'), R + 'velcro')}${cfld(T('zatrzaski', 'snaps'), R + 'snaps')}${cfld(T('elastyczne ściągacze', 'elastic cinches'), R + 'elastic')}${cfld(T('otwory technologiczne', 'technological openings'), R + 'openings')}${cfld(T('dostęp serwisowy', 'service access'), R + 'service_access')}${cfld(T('łatwe czyszczenie', 'easy cleaning'), R + 'easy_clean')}${cfld(T('dopuść obrót wykrojów 90°', 'allow 90° piece rotation'), R + 'allow_rotate_90')}</div>
    <div class="row" style="margin-top:8px"><button class="pri" data-act="recalc">${T('Przelicz konstrukcję', 'Recompute design')}</button></div></div>`;
  if (err) return head('Konstrukcja pokrowca', 'Cover design') + form + err;
  const c = res.construction, secBy = {}; c.sections.forEach(s => secBy[s.id] = s);
  return head('Konstrukcja pokrowca', 'Cover design', T('Etap 5: konstrukcja uzasadniona technicznie (podział, szwy, zakładki, plisy, zapięcia).', 'Stage 5: technically justified construction (split, seams, overlaps, pleats, closures).')) + form +
    c.errors.map(e => `<div class="alert r">${esc(tx(e.text))}</div>`).join('') + c.warnings.map(e => `<div class="alert">${esc(tx(e))}</div>`).join('') + vizBlock(res) +
    `<div class="card"><h3 style="margin-top:0">${T('Uzasadnienie konstrukcji', 'Construction rationale')}</h3><ul>${c.rationale.map(x => `<li>${esc(tx(x))}</li>`).join('')}</ul><p class="mut">${T('Typ konstrukcji', 'Construction type')}: <b>${c.style}</b> · ${T('moduły', 'modules')}: ${c.modules.length}</p></div>
    <div class="card"><h3 style="margin-top:0">${T('Sekcje i moduły', 'Sections and modules')}</h3><div class="tw"><table><tr><th>ID</th><th>${T('Sekcja', 'Section')}</th><th>${T('Rodzaj', 'Kind')}</th><th>${T('Dł. gotowa [mm]', 'Finished length [mm]')}</th><th>${T('Dł. rozwinięta [mm]', 'Developed [mm]')}</th><th>${T('Początek', 'Start')}</th><th>${T('Koniec', 'End')}</th><th>${T('Zapięcie', 'Closure')}</th><th>${T('Moduł', 'Module')}</th></tr>${c.sections.map(s => `<tr><td>${s.id}</td><td>${esc(s.name)}</td><td>${s.kind}${s.bellows ? ` (${s.bellows.n} ${T('plis', 'pleats')} × ${s.bellows.h} mm)` : ''}</td><td>${fmt(s.finished_length, 0)}</td><td>${s.dev_length ? fmt(s.dev_length, 0) : ''}</td><td>${s.start_finish}${s.skirt ? ' ' + s.skirt + ' mm' : ''}</td><td>${s.end_finish}</td><td>${s.closure}</td><td>${s.module}</td></tr>`).join('')}</table></div>
    <h3>${T('Połączenia', 'Joins')}</h3><div class="tw"><table><tr><th>${T('Z', 'From')}</th><th>${T('Do', 'To')}</th><th>${T('Rodzaj', 'Type')}</th><th>${T('Powód', 'Reason')}</th></tr>${c.joins.map(j => `<tr><td>${j.a}</td><td>${j.b}</td><td>${j.type === 'cuff' ? T('zakładka ' + (j.overlap_mm || '') + ' mm + ściągacz', 'overlap ' + (j.overlap_mm || '') + ' mm + cinch') : T('szew stały', 'permanent seam')}</td><td>${j.reason}</td></tr>`).join('') || '<tr><td colspan=4>–</td></tr>'}</table></div></div>`;
};
AFTER.design = () => bindViz();
function bindViz() {
  document.querySelectorAll('[data-vz]').forEach(el => el.onchange = () => { S.viz[el.dataset.vz] = el.checked; go(S.page); });
  const box = $('#vizbox'); if (box && S.viz.view === '3d') { let d = null; box.onpointerdown = e => { d = [e.clientX, e.clientY]; box.setPointerCapture(e.pointerId); };
    box.onpointermove = e => { if (!d) return; S.viz.yaw += (e.clientX - d[0]) * .01; S.viz.pitch = Math.max(-1.4, Math.min(1.4, S.viz.pitch + (e.clientY - d[1]) * .01)); d = [e.clientX, e.clientY]; const wm = box.querySelector('.wm'); const segs = S.project.robot.segments.filter(s => +s.length > 0); box.innerHTML = VIZ.view3d(segs, S.res, { robot: S.viz.robot, cover: S.viz.cover, byModule: S.viz.byModule, seams: S.viz.seams, closures: S.viz.closures }, S.viz.yaw, S.viz.pitch); box.appendChild(wm); };
    box.onpointerup = () => d = null; box.style.cursor = 'grab'; }
}
ACT.vview = a => { S.viz.view = a.dataset.v; go(S.page); };

/* ----- pattern ----- */
PAGE.pattern = async () => {
  const [res, err] = await need(); if (err) return head('Generator wykrojów', 'Pattern generator') + err;
  const b = res.pattern, c = res.consumption, id = S.project.id, L = S.lang; const sel = b.pieces.find(p => p.no === S.sel.piece) || b.pieces[0];
  const fin = f => f.shape === 'rect' ? `${fmt(f.width, 0)} × ${fmt(f.length, 0)}` : f.shape === 'sector' ? `R${fmt(f.R_outer, 0)} / R${fmt(f.R_inner, 0)}, ${fmt(f.angle_deg, 1)}°` : `${fmt(f.width_start, 0)} → ${fmt(f.width_end, 0)} × ${fmt(f.length, 0)}`;
  const rowsK = [['width', T('Szerokość materiału', 'Material width')], ['area', T('Łączna powierzchnia wykrojów', 'Total pattern area')], ['length', T('Szacowana długość materiału', 'Estimated material length')], ['waste', T('Straty materiałowe', 'Material waste')], ['buy', T('Zalecany zakup', 'Recommended purchase')], ['reserve', T('Dodatkowy zapas', 'Additional reserve')]];
  return head('Generator wykrojów', 'Pattern generator', T('Etapy 6–7: wymiary w mm, rozróżnienie wymiaru gotowego i wykroju (zapasy, grubość, skurcz), rozmieszczenie na beli.', 'Stages 6-7: dimensions in mm, finished vs cut size (allowances, thickness, shrinkage), roll layout.')) +
    b.warnings.map(w => `<div class="alert">${esc(tx(w))}</div>`).join('') +
    `<div class="card"><div class="row"><h3 style="margin:0">${T('Eksport', 'Export')}</h3><span class="sp"></span>
    <a href="/api/projects/${id}/export/pattern.pdf?lang=${L}&sheet=A4"><button>PDF 1:1 (A4)</button></a><a href="/api/projects/${id}/export/pattern.pdf?lang=${L}&sheet=A3"><button>PDF 1:1 (A3)</button></a><a href="/api/projects/${id}/export/pattern.dxf"><button>DXF</button></a><a href="/api/projects/${id}/export/marker.svg?lang=${L}"><button>SVG</button></a></div>
    <p class="mut" style="margin:6px 0 0">${T('PDF zawiera stronę z kwadratem kontrolnym 100×100 mm i podział dużych elementów na arkusze 1:1 (zakładka 10 mm, znaczniki rejestracji).', 'The PDF has a page with a 100x100 mm control square and splits large pieces over 1:1 sheets (10 mm overlap, registration marks).')}</p></div>
    <div class="card"><h3 style="margin-top:0">${T('Kalkulator zużycia materiału', 'Material consumption calculator')}</h3>${c.ok ? `<table style="max-width:560px"><tr><th>${T('Parametr', 'Parameter')}</th><th>${T('Wynik', 'Result')}</th></tr>${c.rows.map((r, i) => `<tr><td>${rowsK[i][1]}</td><td class="mono"><b>${r.value}</b> ${r.unit}</td></tr>`).join('')}</table>
    <p class="mut">${esc(tx(c.note))}<br>${T('Rezerwa', 'Reserve')}: ${c.reserve_parts.map(p => esc(tx(p.label)) + ' ' + p.pct + '%').join('; ')} · ${T('strategia rozmieszczenia', 'nesting strategy')}: ${c.strategy}</p>` : `<div class="alert r">${esc(tx(c.error))}</div>`}</div>
    <div class="card"><h3 style="margin-top:0">${T('Mapa rozmieszczenia na beli (skala poglądowa)', 'Roll layout (not to scale)')}</h3><div class="svgbox" id="mk">…</div><div class="mut">${T('Linia ciągła — cięcie; niebieska przerywana — szycie; czerwona kreskowa — zakładki/plisy; strzałka — osnowa.', 'Solid - cut; dashed blue - sew; red dash-dot - overlap/pleats; arrow - warp.')}</div></div>
    <div class="card"><h3 style="margin-top:0">${T('Tabela wymiarów elementów [mm]', 'Piece dimension table [mm]')}</h3><div class="tw"><table><tr><th>${T('Nr', 'No')}</th><th>ID</th><th>${T('Element', 'Piece')}</th><th>${T('Moduł', 'Module')}</th><th>${T('Wymiar gotowy (linia szycia)', 'Finished size (sew line)')}</th><th>${T('Wykrój (prostokąt otaczający)', 'Cut (bounding box)')}</th><th>${T('Zapasy L / P / pocz. / koniec', 'Allowances L / R / start / end')}</th><th>m²</th></tr>
    ${b.pieces.map(p => `<tr data-act="pick" data-n="${p.no}" style="cursor:pointer;${p.no === sel.no ? 'background:var(--bg)' : ''}"><td>${p.no}</td><td>${p.id}</td><td>${esc(tx(p.name))}</td><td>${p.module}</td><td class="mono">${fin(p.finished)}</td><td class="mono">${fmt(p.bbox[0], 0)} × ${fmt(p.bbox[1], 0)}</td><td class="mono">${fmt(p.allowances.left, 0)} / ${fmt(p.allowances.right, 0)} / ${fmt(p.allowances.start, 0)} / ${fmt(p.allowances.end, 0)}</td><td>${p.area_m2.toFixed(3)}</td></tr>`).join('')}</table></div></div>
    <div class="card"><h3 style="margin-top:0">${T('Element', 'Piece')} #${sel.no} ${sel.id}</h3><div class="svgbox" id="pc">…</div>${sel.note ? `<p class="mut">${esc(tx(sel.note))}</p>` : ''}</div>`;
};
AFTER.pattern = async () => { const id = S.project.id; $('#mk').innerHTML = await api(`/projects/${id}/export/marker.inline.svg?lang=${S.lang}`); $('#pc').innerHTML = await api(`/projects/${id}/export/piece-${S.sel.piece}.svg?lang=${S.lang}`); };
ACT.pick = a => { S.sel.piece = +a.dataset.n; go('pattern'); };

/* ----- sewing ----- */
PAGE.sewing = async () => {
  const [res, err] = await need(); if (err) return head('Technologia szycia', 'Sewing configuration') + err;
  const s = res.sewing, th = s.thread, st = s.stitch, mc = s.machine, tt = th.thread;
  const kv = rows => `<table>${rows.map(([k, v]) => `<tr><td class="mut" style="width:38%">${k}</td><td>${v}</td></tr>`).join('')}</table>`;
  return head('Technologia szycia', 'Sewing configuration', T('Etapy 8–9: nić, igła, ścieg, szew, maszyna i dodatki. Wartości z bazy są typowe — wykonaj próbę technologiczną.', 'Stages 8-9: thread, needle, stitch, seam, machine and accessories. Catalogue values are typical - run a technological trial.')) +
    th.warnings.map(w => `<div class="alert ${th.meets_all ? '' : 'r'}">${esc(tx(w))}</div>`).join('') +
    `<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(380px,1fr))"><div class="card"><h3 style="margin-top:0">${T('Nić, igła, ścieg', 'Thread, needle, stitch')} ${conf(tt.confidence)}</h3>${kv([[T('Rodzaj nici', 'Thread type'), esc(tx(tt.name))], [T('Producent / produkt', 'Manufacturer / product'), tt.product || T('do wskazania wg TDS', 'to be specified per TDS') + ' (' + esc(tt.example_suppliers) + ')'], [T('Grubość nici', 'Thread size'), `Tex ${th.tex} (≈ Nm ${th.nm_approx})`], [T('Rozmiar igły', 'Needle size'), `Nm ${th.needle_nm[0]}–${th.needle_nm[1]}`], [T('Rodzaj igły (końcówka)', 'Needle point'), esc(tx(st.needle_point))], [T('System igły', 'Needle system'), esc(tx(st.needle_system))], [T('Rodzaj ściegu', 'Stitch type'), esc(tx(st.stitch_type))], [T('Długość ściegu', 'Stitch length'), `${st.stitch_length_mm} mm (${st.stitches_per_cm}/cm)`], [T('Rodzaj szwu', 'Seam type'), esc(tx(st.seam_type))], [T('Zapas na szew / rąbek', 'Seam / hem allowance'), `${st.allowance} / ${st.hem} mm`], [T('Uszczelnienie szwów', 'Seam sealing'), st.seal ? esc(tx(st.seal.text)) : T('niewymagane', 'not required')], [T('Wzmocnienia', 'Reinforcement'), T('łaty R… przy otworach; ryglowanie końców zamków i narożników zakładek', 'R... patches at openings; bar-tack zipper ends and overlap corners')], [T('Źródło', 'Source'), esc(tx(tt.source))]])}<p class="mut">${esc(tx(tt.notes))}</p></div>
    <div class="card"><h3 style="margin-top:0">${T('Maszyna i ustawienia', 'Machine and settings')}</h3>${mc.error ? `<div class="alert r">${esc(tx(mc.error))}</div>` : kv([[T('Zalecany typ maszyny', 'Recommended machine type'), `<b>${esc(tx(mc.machine.name))}</b> ${conf(mc.machine.confidence)}`], [T('Rodzaj transportu', 'Feed'), mc.machine.feed], [T('Typ stołu', 'Bed'), mc.machine.bed], [T('Wymagana zdolność przeszycia', 'Required penetration capacity'), `${mc.layers} ${T('warstw', 'layers')} × ${fmt(res.material.recommended.effective.thickness_max_mm, 2)} = ${fmt(mc.required_thickness_mm, 1)} mm (${T('zapas ≥ 20% → maszyna ≥', 'margin >= 20% -> machine >=')} ${fmt(mc.required_thickness_mm * 1.2, 1)} mm)`], [T('Wymagane funkcje', 'Required functions'), T('transport złożony/potrójny, regulowany docisk stopki, igła do ' + 'Nm ' + th.needle_nm[1], 'compound/triple feed, adjustable presser foot, needle up to Nm ' + th.needle_nm[1])], [T('Prędkość szycia (start)', 'Sewing speed (start)'), `≤ ${mc.settings.speed_spm} ${T('ściegów/min', 'spm')}`], [T('Napięcie nici', 'Thread tension'), esc(tx(mc.settings.thread_tension))], [T('Docisk stopki', 'Presser foot pressure'), esc(tx(mc.settings.foot_pressure))], [T('Rodzaj stopki', 'Foot type'), esc(tx(mc.settings.foot))], [T('Długość ściegu', 'Stitch length'), st.stitch_length_mm + ' mm'], [T('Igła', 'Needle'), `Nm ${th.needle_nm[0]}–${th.needle_nm[1]}`]])}
    <div class="alert">${T('OBOWIĄZKOWA próba technologiczna na odpadach tego samego materiału i tej samej liczby warstw przed szyciem właściwym — ustawienia powyżej są wartościami początkowymi.', 'A technological trial on offcuts of the same material and layer count is MANDATORY before production sewing - settings above are starting values.')}</div>${mc.alternative ? `<p class="mut">${T('Alternatywa dla szwów wodoszczelnych (powłoki termoplastyczne): ', 'Alternative for waterproof seams (thermoplastic coatings): ')}${esc(tx(mc.alternative.name))}</p>` : ''}</div></div>
    <div class="card"><h3 style="margin-top:0">${T('Dodatki', 'Accessories')}</h3><div class="tw"><table><tr><th>${T('Rodzaj', 'Category')}</th><th>${T('Typ / materiał', 'Type / material')}</th><th>${T('Wymiary', 'Dimensions')}</th><th>${T('Uzasadnienie / kompatybilność', 'Reason / compatibility')}</th><th>${T('Status danych', 'Data status')}</th></tr>
    ${Object.entries(s.accessories).filter(([k, v]) => v).map(([k, v]) => `<tr><td>${k}</td><td>${esc(tx(v.item.name))}<br><span class="mut">${esc(v.item.material)}, ${v.item.tmin_c}…${v.item.tmax_c} °C</span></td><td>${esc(v.item.size)}</td><td>${esc(tx(v.item.notes))} ${v.meets_all ? '' : `<br><span class="badge b-red">${T('niezgodne: ', 'not compatible: ')}${v.fails.map(f => esc(tx(f))).join(', ')}</span>`}</td><td>${conf(v.item.confidence)}</td></tr>`).join('')}</table></div></div>`;
};

/* ----- bom ----- */
PAGE.bom = async () => {
  const [res, err] = await need(); if (err) return head('Lista materiałów', 'Bill of materials') + err; const id = S.project.id;
  return head('Lista materiałów (BOM)', 'Bill of materials', T('Kompletna lista zakupowa na jeden pokrowiec. Ilości wynikają z obliczeń (rozmieszczenie wykrojów, długości szwów × rzędy × długość ściegu).', 'Complete purchase list for one cover. Quantities come from computation (nesting, seam length x rows x stitch length).')) +
    `<div class="card"><div class="row"><span class="sp"></span><a href="/api/projects/${id}/export/bom.csv?lang=${S.lang}"><button>CSV</button></a></div><div class="tw"><table><tr><th>#</th><th>${T('Pozycja', 'Item')}</th><th>${T('Ilość', 'Qty')}</th><th>${T('Jedn.', 'Unit')}</th><th>${T('Specyfikacja', 'Specification')}</th><th>${T('Uzasadnienie', 'Reason')}</th><th>${T('Dane', 'Data')}</th></tr>
    ${res.bom.map((b, i) => `<tr><td>${i + 1}</td><td><b>${esc(tx(b.name))}</b></td><td class="mono">${b.qty}</td><td>${b.unit}</td><td>${esc(tx(b.spec))}</td><td>${esc(tx(b.why))}</td><td>${b.confidence ? conf(b.confidence) : ''}</td></tr>`).join('')}</table></div></div>`;
};

/* ----- docs + validation ----- */
PAGE.docs = async () => {
  const [res, err] = await need(); if (err) return head('Dokumentacja produkcyjna', 'Production documentation') + err; const id = S.project.id;
  const v = res.validation, sm = v.summary, doc = await api(`/projects/${id}/docs?lang=${S.lang}`);
  const blocks = s => s.blocks.map(b => b.t === 'p' ? `<p>${esc(b.text)}</p>` : b.t === 'warn' ? `<div class="alert">${esc(b.text)}</div>` : b.t === 'ol' ? `<ol>${b.items.map(i => `<li>${esc(i)}</li>`).join('')}</ol>` :
    `<div class="tw"><table><tr>${b.head.map(h => `<th>${esc(h)}</th>`).join('')}</tr>${b.rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table></div>`).join('');
  return head('Dokumentacja produkcyjna i walidacja', 'Production documentation and validation', T('Etap 10: system sprawdza poprawność przed zatwierdzeniem. Krytyczne błędy (CZERWONE) blokują zatwierdzenie.', 'Stage 10: the system validates before approval. Critical errors (RED) block approval.')) +
    `<div class="card"><div class="row"><h3 style="margin:0">${T('Walidacja', 'Validation')}</h3><span class="badge b-red">${sm.red} ${T('czerwone', 'red')}</span><span class="badge b-yellow">${sm.yellow} ${T('żółte', 'yellow')}</span><span class="badge b-green">${sm.green} ${T('zielone', 'green')}</span><span class="sp"></span>
    ${S.project.status === 'approved' ? `<span class="badge b-green">${T('PROJEKT ZATWIERDZONY', 'PROJECT APPROVED')}</span>` : `<button class="pri" data-act="approve" ${sm.can_approve ? '' : 'disabled'}>${T('Zatwierdź projekt', 'Approve project')}</button>`}</div>
    ${sm.can_approve ? '' : `<div class="alert r">${T('Zatwierdzenie zablokowane: rozwiąż wszystkie pozycje CZERWONE.', 'Approval blocked: resolve all RED items.')}</div>`}
    <div class="tw"><table><tr><th>${T('Sprawdzenie', 'Check')}</th><th>Status</th><th>${T('Szczegóły', 'Details')}</th><th>${T('Podstawa', 'Basis')}</th></tr>${v.checks.map(c => `<tr><td>${esc(tx(c.label))}</td><td>${badge(c.status)}</td><td>${esc(tx(c.detail))}${(c.notes || []).map(n => `<br>• ${esc(tx(n))}`).join('')}</td><td class="mut">${esc(tx(c.basis))}</td></tr>`).join('')}</table></div>
    <p class="mut">${T('ZIELONY = spełnione i potwierdzone (obliczenie lub dane zweryfikowane dokumentem) · ŻÓŁTY = prawdopodobnie spełnione, wymaga weryfikacji · CZERWONY = niespełnione lub istotne ryzyko.', 'GREEN = met and confirmed (computation or document-verified data) · YELLOW = probably met, needs verification · RED = not met or significant risk.')}</p></div>
    <div class="card"><div class="row"><h3 style="margin:0">${T('Eksport dokumentacji', 'Documentation export')}</h3><span class="sp"></span><a href="/api/projects/${id}/export/docs.pdf?lang=${S.lang}"><button class="pri">PDF</button></a><a href="/api/projects/${id}/export/pattern.pdf?lang=${S.lang}"><button>${T('Wykroje PDF', 'Pattern PDF')}</button></a><a href="/api/projects/${id}/export/pattern.dxf"><button>DXF</button></a><a href="/api/projects/${id}/export/marker.svg?lang=${S.lang}"><button>SVG</button></a><a href="/api/projects/${id}/export/bom.csv?lang=${S.lang}"><button>CSV</button></a></div></div>` +
    doc.sections.map(s => `<div class="card"><h3 style="margin-top:0">${esc(s.title)}</h3>${blocks(s)}</div>`).join('');
};
ACT.approve = async () => { await api(`/projects/${S.project.id}/approve`, { method: 'POST' }); S.project.status = 'approved'; side(); go('docs'); };

/* ----- import from document / URL ----- */
const IMP = { target: 'material', res: null };
const MAT_RATINGS = ['mineral_oil', 'cutting_fluid', 'solvents', 'detergents', 'disinfectants', 'acids', 'alkalis', 'fuels'];
function importCard() {
  const r = IMP.res;
  const recs = (S.libAll || []);
  let h = `<div class="card"><h3 style="margin-top:0">${T('Import danych z dokumentu lub linku (TDS / karta katalogowa)', 'Import data from a document or link (TDS / datasheet)')}</h3>
  <p class="mut">${T('Wgraj PDF/HTML/TXT albo podaj adres URL. Aplikacja zaproponuje wartości wraz z cytatem z dokumentu (reguły tekstowe, bez AI). Do bazy trafia tylko to, co zaznaczysz — i tylko te pola dostają status „zweryfikowane”. Dokument zapisuje się z sumą SHA-256. Pobieranie z URL wymaga dostępu do sieci z serwera.', 'Upload a PDF/HTML/TXT or give a URL. The app proposes values with a quote from the document (text rules, no AI). Only what you tick is stored - and only those fields become "verified". The document is kept with its SHA-256. URL fetch needs network access from the server.')}</p>
  <div class="row"><select id="imt"><option value="material" ${IMP.target === 'material' ? 'selected' : ''}>${T('Materiał', 'Material')}</option><option value="robot" ${IMP.target === 'robot' ? 'selected' : ''}>${T('Robot', 'Robot')}</option></select>
  <input type="file" id="imf" accept=".pdf,.html,.htm,.txt"><button data-act="impfile">${T('Analizuj plik', 'Analyse file')}</button>
  <input id="imu" placeholder="https://…" style="min-width:260px"><button data-act="impurl">${T('Pobierz i analizuj', 'Fetch and analyse')}</button></div>`;
  if (r) {
    if (r.error) h += `<div class="alert r">${esc(r.error)}</div>`;
    else {
      const isM = IMP.target === 'material';
      const base = (S.libAll || []).filter(x => isM ? true : true);
      h += `<div class="alert i">${esc(r.doc.name)} · ${r.doc.chars} ${T('znaków', 'chars')} · sha256 ${r.doc.sha256.slice(0, 12)}…${r.warning ? ' — ' + esc(tx(r.warning)) : ''}</div>`;
      h += `<div class="tw"><table><tr><th></th><th>${T('Pole', 'Field')}</th><th>${T('Wartość', 'Value')}</th><th>${T('Cytat z dokumentu', 'Quote from the document')}</th></tr>` +
        r.findings.map((f, i) => f.kind === 'value' ? `<tr><td><input type="checkbox" class="imc" data-f="${f.field}" checked></td><td>${esc(tx(f.label))}${f.note ? `<div class="mut">${esc(tx(f.note))}</div>` : ''}</td><td><input class="imv" data-f="${f.field}" value="${f.value}" style="width:80px"> ${esc(f.unit)}</td><td class="mut">${esc(f.evidence)}</td></tr>`
          : `<tr><td></td><td>${esc(tx(f.label))}${f.note ? `<div class="mut">${esc(tx(f.note))}</div>` : ''}</td><td>${f.kind === 'info' ? esc(Array.isArray(f.value) ? f.value.join(', ') : f.value) : ''}</td><td class="mut">${esc(f.evidence)}</td></tr>`).join('') + `</table></div>`;
      if (isM) h += `<p><b>${T('Oceny odporności z dokumentu (0–3, puste = pomiń)', 'Ratings from the document (0-3, blank = skip)')}</b> <span class="mut">${T('0 = brak odporności … 3 = bardzo dobra; wpisujesz je Ty na podstawie tabeli w dokumencie', '0 = not resistant ... 3 = very good; you enter them from the document tables')}</span></p><div class="row">${MAT_RATINGS.map(k => `<label>${k} <input class="imr" data-k="chem.${k}" type="number" min="0" max="3" style="width:46px"></label>`).join('')}</div>`;
      h += `<div class="row" style="margin-top:8px"><label>${T('Zastosuj do rekordu', 'Apply to record')} <select id="imrec">${(S.libAll || []).map(x => `<option value="${x.id}">${x.id}</option>`).join('')}</select></label>
      <label>${T('Nazwa produktu (opcjonalnie; wymagana dla nowego rekordu)', 'Product name (optional; required for a new record)')} <input id="imp"></label>
      <label><input type="checkbox" id="imn" checked> ${T('zapisz jako NOWY rekord (rodzina zostaje bez zmian)', 'save as a NEW record (family stays unchanged)')}</label>
      <button class="pri" data-act="impapply">${T('Zastosuj zaznaczone', 'Apply selected')}</button></div>`;
    }
  }
  return h + '</div>';
}
async function impRun(path, body) { IMP.target = $('#imt').value; try { IMP.res = await api(path.replace('{t}', IMP.target), { method: 'POST', body }); } catch (e) { IMP.res = { error: e.message }; } go('library'); }
ACT.impfile = a => { const f = $('#imf').files[0]; if (!f) return alert(T('Wybierz plik', 'Choose a file')); const fd = new FormData(); fd.append('file', f); impRun('/ingest/file?target={t}', fd); };
ACT.impurl = a => { const u = $('#imu').value.trim(); if (!u) return; IMP.target = $('#imt').value; impRun('/ingest/url', { url: u, target: IMP.target }); };
ACT.impapply = async a => {
  const accepted = {}; document.querySelectorAll('.imc').forEach(c => { if (c.checked) accepted[c.dataset.f] = $(`.imv[data-f="${c.dataset.f}"]`).value; });
  const ratings = {}; document.querySelectorAll('.imr').forEach(i => { if (i.value !== '') ratings[i.dataset.k] = i.value; });
  try {
    const out = await api('/ingest/apply', { method: 'POST', body: { target: IMP.target, id: $('#imrec').value, doc: IMP.res.doc, accepted, ratings, product: $('#imp').value.trim() || null, as_new: $('#imn').checked } });
    IMP.res = null; S.lib = IMP.target === 'material' ? 'materials' : 'robots'; S.res = null; go('library'); alert(T('Zapisano rekord: ', 'Record saved: ') + out.id);
  } catch (e) { alert(e.message); }
};

/* ----- library ----- */
PAGE.library = async () => {
  const kinds = [['materials', T('Materiały', 'Materials')], ['threads', T('Nici', 'Threads')], ['machines', T('Maszyny', 'Machines')], ['accessories', T('Dodatki', 'Accessories')], ['robots', T('Roboty', 'Robots')]];
  const l = await api('/db/' + S.lib);
  S.libAll = await api('/db/' + (IMP.target === 'robot' ? 'robots' : 'materials'));
  return head('Baza wiedzy i źródła danych', 'Knowledge base and data sources', T('Każdy rekord ma źródło, datę i poziom pewności. Status „zweryfikowane” wymaga adresu TDS/dokumentu — nie da się go ustawić bez źródła. Edycja zapisuje nadpisanie lokalne (nie zmienia danych wbudowanych).', 'Every record has a source, date and confidence level. "Verified" status requires a TDS/document URL - it cannot be set without a source. Edits are stored as local overrides (built-in data stay untouched).')) + importCard() +
    `<div class="tabs">${kinds.map(([k, n]) => `<button data-act="libk" data-k="${k}" class="${S.lib === k ? 'on' : ''}">${n}</button>`).join('')}</div><div class="card tw"><table><tr><th>ID</th><th>${T('Nazwa', 'Name')}</th><th>${T('Pewność', 'Confidence')}</th><th>${T('Źródło', 'Source')}</th><th>${T('Data', 'Date')}</th><th></th></tr>
    ${l.map(r => `<tr><td class="mono">${r.id}</td><td>${esc(tx(r.name) || (r.manufacturer + ' ' + r.model))}</td><td>${conf(r.confidence)}${r.verified_fields ? `<div class="mut" style="font-size:11px">${esc(r.verified_fields.join(', '))}</div>` : ''}</td><td class="mut">${esc(tx(r.source))}${r.tds_url ? ` — <a href="${esc(r.tds_url)}" target="_blank">TDS</a>` : ''}</td><td>${r.source_date || ''}</td><td><button data-act="libedit" data-id="${r.id}">${T('Edytuj', 'Edit')}</button></td></tr>`).join('')}</table></div>`;
};
ACT.libk = a => { S.lib = a.dataset.k; go('library'); };
ACT.libedit = async a => { const l = await api('/db/' + S.lib); const r = l.find(x => x.id === a.dataset.id); const d = $('#dlg'); const { id, ...rest } = r;
  d.innerHTML = `<h3 style="margin-top:0">${id}</h3><p class="mut">${T('Edytuj JSON. Aby ustawić "confidence":"verified", wpisz "tds_url" (lub "source_document") i opis w "source".', 'Edit the JSON. To set "confidence":"verified", provide "tds_url" (or "source_document") and a description in "source".')}</p><textarea id="lj" style="width:min(820px,85vw);height:55vh" class="mono">${esc(JSON.stringify(rest, null, 1))}</textarea><div class="row" style="margin-top:8px"><button class="pri" id="ls">${T('Zapisz', 'Save')}</button><button id="lc">${T('Anuluj', 'Cancel')}</button></div>`; d.showModal();
  $('#lc').onclick = () => d.close(); $('#ls').onclick = async () => { try { await api(`/db/${S.lib}/${id}`, { method: 'PUT', body: JSON.parse($('#lj').value) }); d.close(); S.res = null; go('library'); } catch (e) { alert(e.message); } }; };

/* ---------- boot ---------- */
(async () => { document.documentElement.lang = S.lang; S.meta = await api('/meta'); side(); go('dashboard'); })();
