/* Thư viện NEU – hiệu ứng & tương tác giao diện (vanilla JS, không phụ thuộc thư viện) */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const ICONS = {
    success: '<path d="m5 12 5 5 9-10"/>', danger: '<path d="M6 6l12 12M18 6 6 18"/>',
    warning: '<path d="M12 4 3 20h18z"/><path d="M12 10v4M12 17v.5"/>', info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/>'
  };
  const svg = (p) => `<svg class="icon" viewBox="0 0 24 24">${p}</svg>`;
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; };

  /* ---- Giao diện sáng / tối ---- */
  $$('.theme-toggle').forEach(b => b.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  }));

  /* ---- Navbar, thanh tiến độ cuộn, nút lên đầu trang ---- */
  const nav = $('.navbar'), bar = $('.scroll-progress'), top = $('.to-top');
  const onScroll = () => {
    const y = scrollY, h = document.documentElement.scrollHeight - innerHeight;
    nav && nav.classList.toggle('scrolled', y > 8);
    bar && (bar.style.transform = `scaleX(${h > 0 ? y / h : 0})`);
    top && top.classList.toggle('show', y > 600);
  };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  top && top.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  const menuBtn = $('.menu-btn'), links = $('.nav-links');
  menuBtn && menuBtn.addEventListener('click', () => links.classList.toggle('open'));

  /* ---- Hiện dần khi cuộn (stagger theo thứ tự trong nhóm) ---- */
  const revealEls = $$('[data-reveal]');
  if ('IntersectionObserver' in window && !reduce) {
    revealEls.forEach(e => {
      if (e.dataset.delay) e.style.setProperty('--d', e.dataset.delay);
      else if (e.parentElement && e.parentElement.hasAttribute('data-stagger')) {
        e.style.setProperty('--d', [...e.parentElement.children].indexOf(e) * 90);
      }
    });
    const io = new IntersectionObserver((entries) => entries.forEach(en => {
      if (en.isIntersecting) {
        const t = en.target; t.classList.add('in'); io.unobserve(t);
        // gỡ reveal sau khi hiện xong để không cản transition riêng (vd: nghiêng 3D)
        setTimeout(() => t.removeAttribute('data-reveal'), 1000 + (parseFloat(t.style.getPropertyValue('--d')) || 0));
      }
    }), { threshold: .12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(e => io.observe(e));
  } else revealEls.forEach(e => e.classList.add('in'));

  /* ---- Số đếm tăng dần ---- */
  const fmt = new Intl.NumberFormat('vi-VN');
  const countUp = (node) => {
    const target = Number(node.dataset.count) || 0, suffix = node.dataset.suffix || '';
    if (reduce || target === 0) { node.textContent = fmt.format(target) + suffix; return; }
    const t0 = performance.now(), dur = 1400;
    const tick = (t) => {
      const p = Math.min((t - t0) / dur, 1), eased = 1 - Math.pow(1 - p, 4);
      node.textContent = fmt.format(Math.round(target * eased)) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const counters = $$('[data-count]');
  if ('IntersectionObserver' in window) {
    const co = new IntersectionObserver((es) => es.forEach(e => { if (e.isIntersecting) { countUp(e.target); co.unobserve(e.target); } }), { threshold: .4 });
    counters.forEach(c => { c.textContent = '0' + (c.dataset.suffix || ''); co.observe(c); });
  } else counters.forEach(countUp);

  /* ---- Nghiêng 3D + ánh sáng theo con trỏ ---- */
  if (fine && !reduce) $$('[data-tilt]').forEach(card => {
    const max = Number(card.dataset.tilt) || 7;
    card.addEventListener('pointermove', (e) => {
      const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      card.style.setProperty('--mx', x * 100 + '%'); card.style.setProperty('--my', y * 100 + '%');
      card.style.transform = `perspective(900px) rotateX(${(.5 - y) * max}deg) rotateY(${(x - .5) * max}deg) translateY(-4px)`;
    });
    card.addEventListener('pointerleave', () => { card.style.transform = ''; });
  });

  /* ---- Hero: blob chạy theo chuột nhẹ ---- */
  const hero = $('.hero');
  if (hero && fine && !reduce) hero.addEventListener('pointermove', (e) => {
    const r = hero.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
    $$('.blob', hero).forEach((b, i) => b.style.translate = `${x * (i ? -50 : 60)}px ${y * (i ? -40 : 50)}px`);
  });

  /* ---- Hiệu ứng gợn sóng khi bấm nút ---- */
  document.addEventListener('pointerdown', (e) => {
    const b = e.target.closest('.btn'); if (!b || b.disabled || reduce) return;
    const r = b.getBoundingClientRect(), s = Math.max(r.width, r.height), rip = el('span', 'ripple');
    rip.style.cssText = `width:${s}px;height:${s}px;left:${e.clientX - r.left - s / 2}px;top:${e.clientY - r.top - s / 2}px`;
    b.appendChild(rip); setTimeout(() => rip.remove(), 650);
  });

  /* ---- Toast từ flash message ---- */
  const stack = $('.toasts');
  const toast = (msg, cat = 'info') => {
    if (!stack) return;
    cat = ICONS[cat] ? cat : 'info';
    const t = el('div', `toast ${cat}`);
    t.setAttribute('role', 'status');
    t.append(el('div', 't-ico', svg(ICONS[cat])), Object.assign(el('div', 't-msg'), { textContent: msg }));
    const x = Object.assign(el('button', 't-close'), { type: 'button', innerHTML: '&times;', ariaLabel: 'Đóng' });
    const close = () => { t.classList.add('out'); setTimeout(() => t.remove(), 350); };
    x.addEventListener('click', close); t.append(x); stack.append(t); setTimeout(close, 5000);
  };
  $$('#flashes .flash-item').forEach((f, i) => setTimeout(() => toast(f.textContent, f.dataset.cat), i * 160));
  window.toast = toast;

  /* ---- Hộp thoại xác nhận (form[data-confirm]) ---- */
  let modal;
  const buildModal = () => {
    modal = el('div', 'modal-back', `<div class="card modal" role="dialog" aria-modal="true">
      <div class="m-ico">!</div><h3>Xác nhận thao tác</h3><p class="muted mt-1 m-text"></p>
      <div class="m-actions"><button type="button" class="btn btn-ghost m-no">Huỷ</button><button type="button" class="btn btn-primary m-yes">Đồng ý</button></div></div>`);
    document.body.append(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });
    $('.m-no', modal).addEventListener('click', () => modal.classList.remove('open'));
    addEventListener('keydown', (e) => { if (e.key === 'Escape') modal.classList.remove('open'); });
  };
  document.addEventListener('submit', (e) => {
    const f = e.target; if (!f.dataset.confirm || f.dataset.ok) return;
    e.preventDefault(); if (!modal) buildModal();
    $('.m-text', modal).textContent = f.dataset.confirm;
    const yes = $('.m-yes', modal), clone = yes.cloneNode(true); yes.replaceWith(clone);
    clone.addEventListener('click', () => { f.dataset.ok = '1'; modal.classList.remove('open'); f.submit(); });
    modal.classList.add('open'); clone.focus();
  });

  /* ---- Placeholder ô tìm kiếm tự đổi ---- */
  const hints = ['Tìm theo tên sách…', 'Tìm theo tác giả…', 'Tìm theo mã ISBN…', 'Thử gõ “Python”…'];
  const heroInput = $('[data-live-search] input[name="q"]');
  if (heroInput && !heroInput.value && !reduce) {
    let i = 0; setInterval(() => { if (document.activeElement !== heroInput) heroInput.placeholder = hints[++i % hints.length]; }, 2600);
  }

  /* ---- Gợi ý tìm kiếm trực tiếp (gọi REST API) ---- */
  const live = $('[data-live-search]');
  if (live) {
    const input = $('input[name="q"]', live), box = $('.suggest', live);
    let timer, ctrl, idx = -1;
    const render = (items, q) => {
      box.replaceChildren();
      if (!items.length) box.append(Object.assign(el('div', 's-empty'), { textContent: `Không có kết quả cho “${q}”` }));
      items.forEach(b => {
        const a = el('a'); a.href = `/books/${b.id}`;
        const info = el('div');
        info.append(Object.assign(el('div', 's-title'), { textContent: b.title }),
          Object.assign(el('div', 's-sub'), { textContent: `${b.author} · ${b.available_copies > 0 ? 'Còn ' + b.available_copies + ' bản' : 'Hết bản'}` }));
        let thumb;
        if (b.cover_url) {
          thumb = el('div', 'mini-cover mini-cover-img');
          const img = document.createElement('img');
          img.src = b.cover_url; img.alt = b.title; img.loading = 'lazy';
          img.onerror = () => { thumb.classList.remove('mini-cover-img'); img.remove(); };
          thumb.append(img);
        } else {
          thumb = el('div', 'mini-cover');
        }
        a.append(thumb, info); box.append(a);
      });
      box.classList.add('open'); idx = -1;
    };
    input.addEventListener('input', () => {
      clearTimeout(timer); const q = input.value.trim();
      if (q.length < 2) { box.classList.remove('open'); return; }
      timer = setTimeout(async () => {
        ctrl && ctrl.abort(); ctrl = new AbortController();
        try {
          const r = await fetch(`/api/v1/books?per_page=5&q=${encodeURIComponent(q)}`, { signal: ctrl.signal });
          render((await r.json()).items || [], q);
        } catch (e) { /* bỏ qua khi huỷ request */ }
      }, 220);
    });
    input.addEventListener('keydown', (e) => {
      const items = $$('a', box); if (!items.length || !box.classList.contains('open')) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); idx = (idx + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items.forEach((a, i) => a.classList.toggle('active', i === idx));
      } else if (e.key === 'Enter' && idx >= 0) { e.preventDefault(); items[idx].click(); }
      else if (e.key === 'Escape') box.classList.remove('open');
    });
    document.addEventListener('click', (e) => { if (!live.contains(e.target)) box.classList.remove('open'); });
  }

  /* ---- Sách cùng thể loại (gọi REST API) ---- */
  const rel = $('[data-related]');
  if (rel) {
    fetch(`/api/v1/books?per_page=5&category=${rel.dataset.category}`).then(r => r.json()).then(d => {
      const items = (d.items || []).filter(b => String(b.id) !== rel.dataset.exclude).slice(0, 4);
      if (!items.length) { rel.closest('section').remove(); return; }
      items.forEach((b, i) => {
        const a = el('a', 'book-card'); a.href = `/books/${b.id}`; a.style.animation = `pageIn .6s var(--ease) ${i * 90}ms both`; a.dataset.tilt = '6';
        let c;
        if (b.cover_url) {
          c = el('div', 'cover cover-img');
          const img = document.createElement('img');
          img.src = b.cover_url; img.alt = `Bìa sách ${b.title}`; img.loading = 'lazy';
          img.onerror = () => {
            c.className = `cover c${(rel.dataset.tone | 0)}`;
            const inner = el('div', 'cover-in');
            inner.append(
              Object.assign(el('span', 'cover-cat'), { textContent: b.category || 'Sách' }),
              Object.assign(el('span', 'cover-title'), { textContent: b.title }),
              Object.assign(el('span', 'cover-author'), { textContent: b.author })
            );
            c.innerHTML = ''; c.append(inner);
          };
          c.append(img);
        } else {
          c = el('div', `cover c${(rel.dataset.tone | 0)}`);
          const inner = el('div', 'cover-in');
          inner.append(Object.assign(el('span', 'cover-cat'), { textContent: b.category || 'Sách' }),
            Object.assign(el('span', 'cover-title'), { textContent: b.title }), Object.assign(el('span', 'cover-author'), { textContent: b.author }));
          c.append(inner);
        }
        const h = Object.assign(el('h3'), { textContent: b.title });
        a.append(c, h, Object.assign(el('div', 'author'), { textContent: b.author })); a.style.color = 'inherit';
        rel.append(a);
        if (fine && !reduce) a.addEventListener('pointermove', (e) => {
          const r = a.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
          a.style.setProperty('--mx', x * 100 + '%'); a.style.setProperty('--my', y * 100 + '%');
        });
      });
    }).catch(() => rel.closest('section').remove());
  }

  /* ---- Trang "Sách của tôi": lọc tab + đếm ngược hạn trả ---- */
  const tabs = $$('.tabs [data-filter]');
  tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.toggle('active', x === t));
    $$('.loan-card').forEach(c => c.classList.toggle('hide', t.dataset.filter !== 'all' && c.dataset.group !== t.dataset.filter));
  }));
  $$('.loan-card[data-due]').forEach(c => {
    const dDue = new Date(c.dataset.due + 'T00:00:00');
    const dNow = new Date(); dNow.setHours(0, 0, 0, 0);
    const days = Math.round((dDue - dNow) / 864e5);
    const start = new Date(c.dataset.start || Date.now());
    const total = Math.max((new Date(c.dataset.due + 'T23:59:59') - start) / 864e5, 1);
    const pct = Math.min(100, Math.max(0, ((new Date() - start) / 864e5 / total) * 100));
    const wrap = $('.due', c), txt = $('.due-text', c); if (!wrap) return;
    wrap.classList.toggle('late', days < 0); wrap.classList.toggle('warn', days >= 0 && days <= 3);
    txt.textContent = days < 0 ? `Quá hạn ${-days} ngày` : days === 0 ? 'Hết hạn hôm nay' : `Còn ${days} ngày`;
    setTimeout(() => wrap.style.setProperty('--p', days < 0 ? 100 : pct), 150);
  });

  /* ---- Donut thống kê ---- */
  $$('.donut[data-p]').forEach(d => setTimeout(() => d.style.setProperty('--p', d.dataset.p), 200));
})();
