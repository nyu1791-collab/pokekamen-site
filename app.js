(() => {
  'use strict';

  const KICK_SVG =
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 2h6v6h3V5h3V2h6v6h-3v3h-3v2h3v3h3v6h-6v-3h-3v-3H9v6H3V2z"/></svg>';

  /* ---------------------------------------------------------
     1. Scroll-Floating Typography (char-float + reveal-float)
     --------------------------------------------------------- */
  function splitCharFloat(el) {
    if (el.dataset.cfDone) return;
    el.dataset.cfDone = '1';
    let idx = 0;

    function wrapNode(node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent || '';
        const frag = document.createDocumentFragment();
        for (const ch of Array.from(text)) {
          if (ch === ' ') {
            const sp = document.createElement('span');
            sp.className = 'cf-space';
            sp.textContent = '\u00A0';
            frag.appendChild(sp);
          } else {
            const span = document.createElement('span');
            span.className = 'cf-char';
            span.style.transitionDelay = `${Math.min(idx * 24, 520)}ms`;
            span.textContent = ch;
            frag.appendChild(span);
            idx += 1;
          }
        }
        return frag;
      }
      if (node.nodeType === Node.ELEMENT_NODE) {
        const clone = node.cloneNode(false);
        for (const child of Array.from(node.childNodes)) {
          clone.appendChild(wrapNode(child));
        }
        return clone;
      }
      return node.cloneNode(true);
    }

    const frag = document.createDocumentFragment();
    for (const child of Array.from(el.childNodes)) {
      frag.appendChild(wrapNode(child));
    }
    el.innerHTML = '';
    el.appendChild(frag);
  }

  document.querySelectorAll('[data-char-float]').forEach(splitCharFloat);

  const revealTargets = Array.from(document.querySelectorAll('.reveal-float, [data-char-float]'));

  function revealVisible() {
    const vh = window.innerHeight || 900;
    for (const el of revealTargets) {
      if (el.classList.contains('is-visible')) continue;
      if (el.dataset.charFloat === 'immediate') {
        el.classList.add('is-visible');
        continue;
      }
      const r = el.getBoundingClientRect();
      if (r.top < vh * 0.96) {
        el.classList.add('is-visible');
      }
    }
  }

  requestAnimationFrame(() => {
    document.querySelectorAll('[data-char-float="immediate"]').forEach((el) => {
      el.classList.add('is-visible');
    });
    revealVisible();
  });

  const progressBar = document.getElementById('scrollProgress');
  let ticking = false;
  function onScroll() {
    ticking = false;
    const sy = window.scrollY || window.pageYOffset || 0;
    const vh = window.innerHeight || 900;
    const docH = Math.max(1, document.documentElement.scrollHeight - vh);
    if (progressBar) {
      progressBar.style.width = `${Math.min(100, (sy / docH) * 100).toFixed(2)}%`;
    }
    revealVisible();
  }
  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(onScroll);
      }
    },
    { passive: true }
  );
  onScroll();

  /* ---------------------------------------------------------
     2. Live Status (Kick / TwitCasting / X / YouTube) Renderer
     --------------------------------------------------------- */
  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatNumber(n) {
    if (n === null || n === undefined || Number.isNaN(Number(n))) return '';
    return Number(n).toLocaleString('ja-JP');
  }

  function applyPreviewOverride(data) {
    const mode = new URLSearchParams(window.location.search).get('preview');
    if (!mode) return data;
    const cloned = JSON.parse(JSON.stringify(data));
    if (mode === 'live-kick' || mode === 'live-all') {
      cloned.kick = Object.assign({}, cloned.kick, {
        is_live: true,
        title: cloned.kick?.title || '【テスト表示】ポケカメン Kick 生配信中！',
        viewers: cloned.kick?.viewers || 6197,
        category: cloned.kick?.category || 'Just Chatting',
        thumbnail: cloned.kick?.thumbnail || './assets/poke_banner_x.jpg',
        url: 'https://kick.com/pokekamen',
      });
    }
    if (mode === 'live-tc' || mode === 'live-all') {
      cloned.twitcasting = Object.assign({}, cloned.twitcasting, {
        is_live: true,
        title: '【テスト表示】緊急キャス配信！相談・暴露受付中',
        viewers: 3420,
        thumbnail: './assets/poke_banner_x.jpg',
        url: 'https://twitcasting.tv/gc5r5ogikgv0yvz',
      });
    }
    if (mode === 'offline') {
      cloned.kick = Object.assign({}, cloned.kick, { is_live: false });
      cloned.twitcasting = Object.assign({}, cloned.twitcasting, { is_live: false });
    }
    return cloned;
  }

  function applyLiveData(rawData) {
    if (!rawData) return;
    const data = applyPreviewOverride(rawData);
    const kick = data.kick || {};
    const tc = data.twitcasting || {};
    const xData = data.x || {};
    const yt = data.youtube || {};

    // --- Header Buttons & Hero Jump Pills (LIVE "pikkon-pikkon" pulse) ---
    const headerKickBtn = document.getElementById('headerKickBtn');
    const headerTcBtn = document.getElementById('headerTcBtn');
    const jumpKick = document.getElementById('jumpKick');
    const jumpTc = document.getElementById('jumpTc');

    if (headerKickBtn) {
      headerKickBtn.href = kick.url || 'https://kick.com/pokekamen';
      headerKickBtn.classList.toggle('is-live-pulse', Boolean(kick.is_live));
      headerKickBtn.innerHTML = `${KICK_SVG}<span>Kick</span>${kick.is_live ? '<em class="hdr-live-chip">LIVE</em>' : ''}`;
    }

    if (headerTcBtn) {
      headerTcBtn.href = tc.url || 'https://twitcasting.tv/gc5r5ogikgv0yvz';
      headerTcBtn.classList.toggle('is-live-pulse', Boolean(tc.is_live));
      headerTcBtn.innerHTML = `<img src="./assets/logo_twitcasting.png" alt="ツイキャス" /><span>ツイキャス</span>${tc.is_live ? '<em class="hdr-live-chip">LIVE</em>' : ''}`;
    }

    if (jumpKick) {
      jumpKick.classList.toggle('is-live-pulse', Boolean(kick.is_live));
      jumpKick.innerHTML = kick.is_live ? 'Kick 配信 <em class="hdr-live-chip">LIVE</em>' : 'Kick 配信';
    }

    if (jumpTc) {
      jumpTc.classList.toggle('is-live-pulse', Boolean(tc.is_live));
      jumpTc.innerHTML = tc.is_live ? 'ツイキャス <em class="hdr-live-chip">LIVE</em>' : 'ツイキャス';
    }

    // --- Kick Frame ---
    const kickFrame = document.getElementById('kick-section');
    const kickBadge = document.getElementById('kickBadge');
    const kickDot = document.getElementById('kickDot');
    const kickBadgeText = document.getElementById('kickBadgeText');
    const kickFollowers = document.getElementById('kickFollowers');
    const kickTitle = document.getElementById('kickStreamTitle');
    const kickMeta = document.getElementById('kickStreamMeta');
    const kickCta = document.getElementById('kickCta');
    const kickThumbWrap = document.getElementById('kickThumbWrap');
    const kickThumbImg = document.getElementById('kickThumbImg');
    const kickAvatar = document.getElementById('kickAvatar');
    const kickProfileName = document.getElementById('kickProfileName');
    const kickProfileBio = document.getElementById('kickProfileBio');

    if (kickFollowers && kick.followers) {
      kickFollowers.textContent = `kick.com/pokekamen ・ フォロワー ${formatNumber(kick.followers)}`;
    }
    if (kickAvatar && kick.avatar) {
      kickAvatar.onerror = () => {
        kickAvatar.onerror = null;
        kickAvatar.src = './assets/poke_avatar_kick.webp';
      };
      kickAvatar.src = kick.avatar;
    }
    if (kickProfileName && kick.username) {
      kickProfileName.textContent = `${kick.username}（Kick プロフィール）`;
    }
    if (kickProfileBio && kick.bio) {
      kickProfileBio.textContent = kick.bio;
    }
    if (kickCta) {
      kickCta.href = kick.url || 'https://kick.com/pokekamen';
    }

    if (kickFrame && kickBadge && kickDot && kickBadgeText && kickTitle && kickMeta && kickCta) {
      if (kick.is_live) {
        kickFrame.classList.add('is-live');
        kickBadge.className = 'live-badge on-kick';
        kickDot.className = 'pulse-dot live';
        kickBadgeText.textContent = 'LIVE 配信中';
        kickTitle.textContent = kick.title || 'Kick で生配信中！';
        const cat = kick.category ? ` ・ ${kick.category}` : '';
        kickMeta.textContent = `現在 ${formatNumber(kick.viewers)} 人が視聴中${cat}`;
        kickCta.innerHTML = '<span>今すぐ Kick ライブを見る</span><span aria-hidden="true">↗</span>';
        if (kickThumbWrap && kickThumbImg && kick.thumbnail) {
          kickThumbImg.onerror = () => {
            kickThumbWrap.classList.remove('show');
          };
          kickThumbImg.src = kick.thumbnail;
          kickThumbWrap.classList.add('show');
        } else if (kickThumbWrap && kickThumbImg) {
          kickThumbWrap.classList.remove('show');
          kickThumbImg.removeAttribute('src');
        }
      } else {
        kickFrame.classList.remove('is-live');
        kickBadge.className = 'live-badge';
        kickDot.className = 'pulse-dot';
        kickBadgeText.textContent = 'OFFLINE';
        kickTitle.textContent = '現在はオフラインです';
        kickMeta.textContent = '配信が始まると自動で「LIVE 配信中」＋視聴者数に切り替わります';
        kickCta.innerHTML = '<span>Kick チャンネルを開く</span><span aria-hidden="true">↗</span>';
        if (kickThumbWrap) kickThumbWrap.classList.remove('show');
        if (kickThumbImg) kickThumbImg.removeAttribute('src');
      }
    }

    // --- Kick Latest 3 VODs ---
    const kickVodGrid = document.getElementById('kickVodGrid');
    if (kickVodGrid && Array.isArray(kick.videos) && kick.videos.length > 0) {
      kickVodGrid.innerHTML = kick.videos
        .slice(0, 3)
        .map(
          (v, i) => `
          <a class="recent-card" href="${escapeHtml(v.url || 'https://kick.com/pokekamen/videos')}" target="_blank" rel="noopener noreferrer">
            <div class="recent-thumb">
              <img src="${escapeHtml(v.thumbnail || './assets/poke_avatar_kick.webp')}" alt="${escapeHtml(v.title)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='./assets/poke_avatar_kick.webp';" />
              <span class="recent-tag-tl">KICK ${i + 1}</span>
              ${v.duration ? `<span class="recent-tag-br">${escapeHtml(v.duration)}</span>` : ''}
            </div>
            <div class="recent-body">
              <div class="recent-meta"><span>${escapeHtml(v.date || '')}</span><span>${escapeHtml(v.category || '')}</span></div>
              <div class="recent-title">${escapeHtml(v.title || 'Kick 過去配信')}</div>
            </div>
          </a>
        `
        )
        .join('');
    }

    // --- TwitCasting Frame ---
    const tcFrame = document.getElementById('twitcasting-section');
    const tcBadge = document.getElementById('tcBadge');
    const tcDot = document.getElementById('tcDot');
    const tcBadgeText = document.getElementById('tcBadgeText');
    const tcFollowers = document.getElementById('tcFollowers');
    const tcTitle = document.getElementById('tcStreamTitle');
    const tcMeta = document.getElementById('tcStreamMeta');
    const tcCta = document.getElementById('tcCta');
    const tcThumbWrap = document.getElementById('tcThumbWrap');
    const tcThumbImg = document.getElementById('tcThumbImg');
    const tcAvatar = document.getElementById('tcAvatar');
    const tcProfileName = document.getElementById('tcProfileName');
    const tcProfileBio = document.getElementById('tcProfileBio');

    if (tcCta) {
      tcCta.href = tc.url || 'https://twitcasting.tv/gc5r5ogikgv0yvz';
    }
    if (tcFollowers) {
      const supText = tc.supporters ? `サポーター ${tc.supporters}` : '';
      const lvText = tc.level ? `Lv.${tc.level}` : '';
      const metaBits = ['twitcasting.tv/gc5r5ogikgv0yvz', supText, lvText].filter(Boolean);
      tcFollowers.textContent = metaBits.join(' ・ ');
    }
    if (tcAvatar && tc.avatar) {
      tcAvatar.onerror = () => {
        tcAvatar.onerror = null;
        tcAvatar.src = './assets/poke_avatar_tc.jpg';
      };
      tcAvatar.src = tc.avatar;
    }
    if (tcProfileName && tc.name) {
      tcProfileName.textContent = `${tc.name}（ツイキャスプロフィール）`;
    }
    if (tcProfileBio && tc.bio) {
      tcProfileBio.textContent = tc.bio;
    }

    if (tcFrame && tcBadge && tcDot && tcBadgeText && tcTitle && tcMeta && tcCta) {
      if (tc.is_live) {
        tcFrame.classList.add('is-live');
        tcBadge.className = 'live-badge on-twitcasting';
        tcDot.className = 'pulse-dot live-tc';
        tcBadgeText.textContent = 'LIVE 配信中';
        tcTitle.textContent = tc.title || 'ツイキャスで生配信中！';
        tcMeta.textContent = tc.viewers ? `現在 ${formatNumber(tc.viewers)} 人が視聴中` : '今すぐ参加できます';
        tcCta.innerHTML = '<span>今すぐツイキャスを見る</span><span aria-hidden="true">↗</span>';
        if (tcThumbWrap && tcThumbImg && tc.thumbnail) {
          tcThumbImg.onerror = () => {
            tcThumbWrap.classList.remove('show');
          };
          tcThumbImg.src = tc.thumbnail;
          tcThumbWrap.classList.add('show');
        } else if (tcThumbWrap && tcThumbImg) {
          tcThumbWrap.classList.remove('show');
          tcThumbImg.removeAttribute('src');
        }
      } else {
        tcFrame.classList.remove('is-live');
        tcBadge.className = 'live-badge';
        tcDot.className = 'pulse-dot';
        tcBadgeText.textContent = 'OFFLINE';
        tcTitle.textContent = '現在はオフラインです';
        tcMeta.textContent = '配信が始まると自動で「LIVE 配信中」に切り替わります';
        tcCta.innerHTML = '<span>ツイキャスを開く</span><span aria-hidden="true">↗</span>';
        if (tcThumbWrap) tcThumbWrap.classList.remove('show');
        if (tcThumbImg) tcThumbImg.removeAttribute('src');
      }
    }

    // --- TwitCasting Latest 3 Recorded Movies ---
    const tcMovieGrid = document.getElementById('tcMovieGrid');
    if (tcMovieGrid && Array.isArray(tc.movies) && tc.movies.length > 0) {
      tcMovieGrid.innerHTML = tc.movies
        .slice(0, 3)
        .map(
          (m, i) => `
          <a class="recent-card" href="${escapeHtml(m.url || 'https://twitcasting.tv/gc5r5ogikgv0yvz/show/')}" target="_blank" rel="noopener noreferrer">
            <div class="recent-thumb">
              <img src="${escapeHtml(m.thumbnail || './assets/poke_avatar_tc.jpg')}" alt="${escapeHtml(m.title)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='./assets/poke_avatar_tc.jpg';" />
              <span class="recent-tag-tl">CAS ${i + 1}</span>
              ${m.views ? `<span class="recent-tag-br">${formatNumber(m.views)} 視聴</span>` : (m.duration ? `<span class="recent-tag-br">${escapeHtml(m.duration)}</span>` : '')}
            </div>
            <div class="recent-body">
              <div class="recent-meta"><span>${escapeHtml(m.date || '')}</span>${m.duration ? `<span>${escapeHtml(m.duration)}</span>` : ''}</div>
              <div class="recent-title">${escapeHtml(m.title || 'ツイキャス配信アーカイブ')}</div>
            </div>
          </a>
        `
        )
        .join('');
    }

    // --- X Profile Update ---
    const xFollowers = document.getElementById('xFollowers');
    const xProfileName = document.getElementById('xProfileName');
    const xProfileBio = document.getElementById('xProfileBio');
    if (xFollowers && xData.followers) {
      xFollowers.textContent = `@GC5R5OGIKgV0yvz ・ フォロワー ${formatNumber(xData.followers)}`;
    }
    if (xProfileName && xData.name) {
      xProfileName.textContent = xData.name;
    }
    if (xProfileBio && xData.bio) {
      xProfileBio.textContent = xData.bio;
    }

    // --- YouTube Latest 3 Regular Videos ---
    const ytGrid = document.getElementById('ytGrid');
    if (ytGrid && Array.isArray(yt.videos) && yt.videos.length > 0) {
      ytGrid.innerHTML = yt.videos
        .slice(0, 3)
        .map(
          (v, i) => `
          <a class="yt-card reveal-float is-visible" href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer">
            <div class="yt-thumb-wrap">
              <img src="${escapeHtml(v.thumbnail)}" alt="${escapeHtml(v.title)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='./assets/poke_banner_x.jpg';" />
              <span class="yt-new-tag">NEW ${i + 1}</span>
              <div class="yt-play-badge">
                <span class="yt-play-btn">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z"/></svg>
                </span>
              </div>
            </div>
            <div class="yt-info">
              <span class="yt-date">${escapeHtml(v.published)}</span>
              <h3 class="yt-title">${escapeHtml(v.title)}</h3>
            </div>
          </a>
        `
        )
        .join('');
    }

    const updatedEl = document.getElementById('lastUpdated');
    if (updatedEl && data.fetched_at) {
      updatedEl.textContent = `最終確認：${data.fetched_at}（自動更新）`;
    }
  }

  let isFetching = false;
  let lastFetchAt = 0;
  let useStaticJson = window.location.hostname.endsWith('.github.io');

  async function fetchLiveStatus(force = false) {
    if (window.location.protocol === 'file:') return;
    if (isFetching) return;
    isFetching = true;
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 12000) : null;
    try {
      let res = null;
      if (!useStaticJson) {
        res = await fetch(`/api/live-status${force ? '?refresh=1' : ''}`, {
          cache: 'no-store',
          signal: controller ? controller.signal : undefined,
        });
        if (!res.ok) {
          useStaticJson = true;
          res = null;
        }
      }
      if (!res) {
        res = await fetch(`./live-status.json?t=${Date.now()}`, {
          cache: 'no-store',
          signal: controller ? controller.signal : undefined,
        });
      }
      if (res && res.ok) {
        const data = await res.json();
        applyLiveData(data);
        lastFetchAt = Date.now();
      }
    } catch {
      // 一時的な通信エラー時でも画面を壊さず現在の表示を維持
    } finally {
      if (timer) clearTimeout(timer);
      isFetching = false;
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && Date.now() - lastFetchAt > 20000) {
      fetchLiveStatus(false);
    }
  });

  fetchLiveStatus(false);
  setInterval(() => fetchLiveStatus(false), 60000);
})();
