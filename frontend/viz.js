/* Schematic visualisation (simplified planar model). NOT a dimensioned CAD model. */
const VIZ = (() => {
  const PAL = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#ec4899', '#84cc16'];
  const ease = s => { let c = 10; if (s.hot_c != null && s.hot_c !== '' && +s.hot_c >= 60) c += 10; if (s.cooling_vent) c += 10; const h = +s.protrusion_h || 0; return h ? Math.max(c, h + 5) : c; };
  const r0 = s => (s.shape === 'box' ? Math.hypot(+s.width, +s.depth) / 2 : (+s.d1) / 2);
  const r1 = s => s.shape === 'frustum' ? (+s.d2) / 2 : r0(s);
  function chain(segs) {
    let x = 0, y = 0, ang = 90; const out = [];
    segs.forEach(s => {
      ang += +s.neutral_angle || 0; const L = +s.length || 0, c = Math.cos(ang * Math.PI / 180), d = Math.sin(ang * Math.PI / 180);
      out.push({ s, p0: [x, y], p1: [x + L * c, y + L * d], dx: c, dy: d, L }); x += L * c; y += L * d;
    });
    return out;
  }
  const along = (c, a) => [c.p0[0] + c.dx * a, c.p0[1] + c.dy * a];
  function quad(c, a, b, ra, rb) {
    const p = along(c, a), q = along(c, b), nx = -c.dy, ny = c.dx;
    return [[p[0] + nx * ra, p[1] + ny * ra], [q[0] + nx * rb, q[1] + ny * rb], [q[0] - nx * rb, q[1] - ny * rb], [p[0] - nx * ra, p[1] - ny * ra]];
  }
  function circle(cx, cy, r, n = 28) { const o = []; for (let i = 0; i < n; i++) { const t = 2 * Math.PI * i / n; o.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]); } return o; }
  function items(segs, res, opt) {
    const ch = chain(segs); const out = []; const secs = res && res.construction && res.construction.sections;
    if (opt.robot) ch.forEach((c, i) => { if (c.L > 0) out.push({ ci: i, a: 0, b: c.L, ra: r0(c.s), rb: r1(c.s), fill: '#9aa5b5', op: .55, stroke: '#566', layer: 'robot' }); });
    if (opt.cover) {
      if (secs && secs.length) {
        const mods = {}; (res.construction.modules || []).forEach((m, i) => mods[m.id] = i);
        secs.forEach(sc => {
          const col = opt.byModule ? PAL[mods[sc.module] % PAL.length] : '#2f6fdb';
          if (sc.kind === 'bellows') {
            const i = sc.seg, c = ch[i], n = ch[i + 1], h = sc.finished_length / 2, e = Math.max(ease(c.s), ease(n.s)), rr = Math.max(r0(c.s), r1(c.s), r0(n.s)) + e;
            out.push({ ci: i, a: c.L - h, b: c.L, ra: rr, rb: rr, fill: '#f59e0b', op: .6, stroke: '#a60', layer: 'cover', bell: true, sec: sc });
            out.push({ ci: i + 1, a: 0, b: h, ra: rr, rb: rr, fill: '#f59e0b', op: .6, stroke: '#a60', layer: 'cover', bell: true, sec: sc });
          } else {
            const c = ch[sc.seg], e = ease(c.s), a = sc.start_offset || 0, b = a + sc.finished_length;
            out.push({ ci: sc.seg, a, b, ra: r0(c.s) + e, rb: r1(c.s) + e, fill: col, op: .35, stroke: col, layer: 'cover', sec: sc });
          }
        });
      } else ch.forEach((c, i) => { if (c.s.cover !== false && c.L > 0) { const e = ease(c.s); out.push({ ci: i, a: 0, b: c.L, ra: r0(c.s) + e, rb: r1(c.s) + e, fill: '#2f6fdb', op: .3, stroke: '#2f6fdb', layer: 'cover' }); } });
    }
    return { ch, out };
  }
  function fit(polys, w = 760, h = 520, pad = 30) {
    const xs = [], ys = []; polys.forEach(p => p.pts.forEach(q => { xs.push(q[0]); ys.push(q[1]); }));
    if (!xs.length) return { vb: '0 0 10 10', f: q => q };
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const s = Math.min((w - 2 * pad) / Math.max(1, x1 - x0), (h - 2 * pad) / Math.max(1, y1 - y0));
    return { vb: `0 0 ${w} ${h}`, s, f: q => [pad + (q[0] - x0) * s + ((w - 2 * pad) - (x1 - x0) * s) / 2, h - pad - (q[1] - y0) * s - ((h - 2 * pad) - (y1 - y0) * s) / 2] };
  }
  const pts2 = (p, f) => p.pts.map(q => f(q).map(v => v.toFixed(1)).join(',')).join(' ');
  const svgPoly = (p, f) => `<polygon points="${pts2(p, f)}" fill="${p.fill || 'none'}" fill-opacity="${p.op ?? 1}" stroke="${p.stroke || '#333'}" stroke-width="${p.sw || 1}"/>`;
  const svgLine = (p, f) => `<polyline points="${pts2(p, f)}" fill="none" stroke="${p.stroke}" stroke-width="${p.sw || 1}" ${p.dash ? `stroke-dasharray="${p.dash}"` : ''}/>`;

  function view2d(view, segs, res, opt) {
    const { ch, out } = items(segs, res, opt); const polys = [];
    out.forEach(it => {
      const c = ch[it.ci]; let pts; const mid = along(c, (it.a + it.b) / 2), rr = Math.max(it.ra, it.rb);
      if (view === 'front') pts = quad(c, it.a, it.b, it.ra, it.rb);
      else if (view === 'side') {
        if (Math.abs(c.dx) > 3 * Math.abs(c.dy)) pts = circle(0, mid[1], rr);
        else { const p = along(c, it.a), q = along(c, it.b); pts = [[-rr, p[1]], [rr, p[1]], [rr, q[1]], [-rr, q[1]]]; }
      } else {
        if (Math.abs(c.dy) > 3 * Math.abs(c.dx)) pts = circle(mid[0], 0, rr);
        else { const p = along(c, it.a), q = along(c, it.b); pts = [[p[0], -rr], [q[0], -rr], [q[0], rr], [p[0], rr]]; }
      }
      polys.push({ pts, fill: it.fill, op: it.op, stroke: it.stroke });
    });
    const lines = [];
    const C = res && res.construction;
    if (view === 'front' && C && opt.seams) C.sections.forEach(sc => { if (sc.kind === 'bellows') return; const c = ch[sc.seg], r = r0(c.s) + ease(c.s);
      [sc.start_offset || 0, (sc.start_offset || 0) + sc.finished_length].forEach(a => { const p = along(c, a); lines.push({ pts: [[p[0] - c.dy * r, p[1] + c.dx * r], [p[0] + c.dy * r, p[1] - c.dx * r]], stroke: '#d23a3a', sw: 2 }); }); });
    if (view === 'front' && opt.closures && C) C.sections.forEach(sc => { const c = ch[sc.seg], r = r0(c.s) + ease(c.s); const a = sc.start_offset || 0, b = a + sc.finished_length;
      const p = along(c, a), q = along(c, b); lines.push({ pts: [[p[0] - c.dy * r, p[1] + c.dx * r], [q[0] - c.dy * r, q[1] + c.dx * r]], stroke: sc.closure === 'zipper' ? '#1a8f4a' : '#7a3fd0', sw: 2.5, dash: '5 3' }); });
    const F = fit(polys.concat(lines));
    let s = `<svg viewBox="${F.vb}" width="100%" xmlns="http://www.w3.org/2000/svg">`;
    polys.forEach(p => s += svgPoly(p, F.f)); lines.forEach(l => s += svgLine(l, F.f));
    if (opt.labels && view === 'front') ch.forEach(c => { const m = F.f(along(c, c.L / 2)); s += `<text x="${(m[0] + 6).toFixed(0)}" y="${m[1].toFixed(0)}" font-size="11" fill="#333">${c.s.name || ''}</text>`; });
    if (F.s) s += `<line x1="20" y1="506" x2="${(20 + 100 * F.s).toFixed(1)}" y2="506" stroke="#333" stroke-width="2"/><text x="20" y="498" font-size="10" fill="#333">100 mm</text>`;
    return s + '</svg>';
  }
  function view3d(segs, res, opt, yaw, pitch) {
    const { ch, out } = items(segs, res, opt); const lines = [];
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const rot = (X, Y, Z) => { const X1 = X * cy - Y * sy, Y1 = X * sy + Y * cy; return [X1, Z * cp - Y1 * sp]; };
    out.forEach(it => {
      const c = ch[it.ci]; const ring = (a, r) => { const p = along(c, a), pts = []; for (let i = 0; i <= 24; i++) { const t = 2 * Math.PI * i / 24; const u = Math.cos(t) * r, v = Math.sin(t) * r; pts.push(rot(p[0] + v * -c.dy, u, p[1] + v * c.dx)); } return pts; };
      const A = ring(it.a, it.ra), B = ring(it.b, it.rb); const col = it.layer === 'robot' ? '#667' : it.stroke;
      lines.push({ pts: A, stroke: col, sw: 1 }, { pts: B, stroke: col, sw: 1 });
      for (let i = 0; i < 24; i += 3) lines.push({ pts: [A[i], B[i]], stroke: col, sw: .6 });
      if (opt.seams && it.sec && !it.bell) lines.push({ pts: A, stroke: '#d23a3a', sw: 2.2 });
      if (opt.closures && it.sec && it.layer === 'cover') lines.push({ pts: [A[0], B[0]], stroke: it.sec.closure === 'zipper' ? '#1a8f4a' : '#7a3fd0', sw: 3, dash: '5 3' });
    });
    const F = fit(lines);
    let s = `<svg viewBox="${F.vb}" width="100%" xmlns="http://www.w3.org/2000/svg">`; lines.forEach(l => s += svgLine(l, F.f)); return s + '</svg>';
  }
  function legend(res) {
    if (!(res && res.construction)) return '';
    return (res.construction.modules || []).map((m, i) => `<span style="margin-right:12px"><i class="sw" style="background:${PAL[i % PAL.length]}"></i>${m.id}</span>`).join('') + '<span><i class="sw" style="background:#f59e0b"></i>bellows</span>';
  }
  return { view2d, view3d, legend };
})();
