/* 数据层：优先走后端 API；后端不可用时回落到本地 app-data.js 静态副本。
   数据源唯一原则：正常情况下不读本地副本，本地副本只作断网/后端挂掉的降级。 */
(function (global) {
  'use strict';

  var EP = {
    health: '/api/health',
    terms: '/api/solar-terms/',
    constits: '/api/constitutions/',
    questions: '/api/constitutions/questions',
    ingredients: '/api/ingredients/',
    dishes: '/api/dishes/',
    profile: '/api/config/profile',
    groups: '/api/config/groups',
    rules: '/api/config/rules',
    chronic: '/api/config/chronic',
    generate: '/api/banquet/generate'
  };

  var DEFAULT_ORIGIN = 'http://127.0.0.1:8000';

  /* ---- 请求基址 ----
     用 file:// 双击打开时，'/api/xxx' 会被解析成 file:///api/xxx，fetch 必然失败。
     这里自动补成后端地址；正常经 http://127.0.0.1:8000 打开时基址为空，行为不变。
     需要连别的机器上的后端，可在控制台执行 localStorage.setItem('YS_API_BASE','http://192.168.x.x:8000') */
  var BASE = '';
  try {
    if (global.location && global.location.protocol === 'file:') BASE = DEFAULT_ORIGIN;
    var ov = global.localStorage && global.localStorage.getItem('YS_API_BASE');
    if (ov) BASE = ov;
  } catch (e) { /* 隐私模式下 localStorage 不可用，忽略 */ }

  function url(path) { return path.charAt(0) === '/' ? BASE + path : path; }

  function isFileProtocol() {
    try { return !!global.location && global.location.protocol === 'file:'; } catch (e) { return false; }
  }

  /* 统一错误类型：上层靠 kind 决定给用户看什么，而不是靠解析 message 文本 */
  function ApiError(kind, message, extra) {
    var e = new Error(message);
    e.name = 'ApiError';
    e.kind = kind;
    if (extra) Object.keys(extra).forEach(function (k) { e[k] = extra[k]; });
    return e;
  }

  function request(path, opt, timeout) {
    var ctrl = (typeof AbortController === 'function') ? new AbortController() : null;
    var timer = null;
    if (ctrl && timeout) {
      timer = setTimeout(function () { ctrl.abort(); }, timeout);
    }
    var init = opt || {};
    if (ctrl) init.signal = ctrl.signal;

    /* fetch 缺失或被禁用时，调用会同步抛错（不进 Promise 链），
       那样 .catch 接不到、整个应用直接白屏。这里一律转成 rejected promise。 */
    var p;
    try {
      p = fetch(url(path), init);
    } catch (e) {
      p = Promise.reject(e);
    }

    return Promise.resolve(p).then(function (r) {
      if (!r.ok) {
        return r.text().catch(function () { return ''; }).then(function (t) {
          var detail = '';
          try { detail = (JSON.parse(t) || {}).detail || t; } catch (e) { detail = t; }
          throw ApiError('http', '后端返回 ' + r.status, {
            status: r.status, path: path, detail: String(detail || '').slice(0, 300)
          });
        });
      }
      return r.json().catch(function () {
        throw ApiError('parse', '响应不是合法 JSON', { path: path });
      });
    }).catch(function (e) {
      if (e && e.kind) throw e;                       // 已分类，原样抛
      if (e && e.name === 'AbortError') {
        throw ApiError('timeout', '请求超时（' + Math.round(timeout / 1000) + ' 秒无响应）', { path: path });
      }
      /* fetch 在网络层失败时抛的是 TypeError（Chrome 文案即 "Failed to fetch"） */
      throw ApiError('network', '连不上后端（' + (e && e.message ? e.message : 'unknown') + '）', {
        path: path, raw: String(e && e.message || e)
      });
    }).then(function (x) {
      if (timer) clearTimeout(timer);
      return x;
    }, function (e) {
      if (timer) clearTimeout(timer);
      throw e;
    });
  }

  function get(path, timeout) {
    return request(path, { headers: { Accept: 'application/json' } }, timeout || 10000);
  }

  function post(path, body, timeout) {
    return request(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }, timeout || 20000);
  }

  /* 本地静态副本降级：app-data.js 里的全局量 */
  function fromLocal() {
    var ok = typeof global.SOLAR_TERMS !== 'undefined' && typeof global.DISHES !== 'undefined';
    if (!ok) throw new Error('本地副本不可用');
    var groups = [];
    var sgc = (global.RULES || {}).special_group_contraindications || {};
    Object.keys(sgc).forEach(function (k) { groups.push({ key: k, name: (sgc[k] || {}).name || k }); });
    return {
      terms: global.SOLAR_TERMS,
      constits: global.CONSTITUTIONS,
      questions: global.QUESTIONS,
      ingredients: global.INGREDIENTS,
      dishes: global.DISHES,
      rules: global.RULES || {},
      profile: null,
      groups: groups,
      chronic: (global.RULES || {}).chronic_diet_guidance || {},
      source: 'local'
    };
  }

  /* 首屏加载：先花 5 秒探一次 /api/health，探不通就直接走本地副本，
     不用等 9 个接口逐个超时。探通了再并发取全部数据。 */
  function loadAll() {
    return get(EP.health, 5000).then(function () {
      return Promise.all([
        get(EP.terms), get(EP.constits), get(EP.questions), get(EP.ingredients),
        get(EP.dishes), get(EP.profile), get(EP.groups), get(EP.rules), get(EP.chronic)
      ]).then(function (r) {
        return {
          terms: r[0], constits: r[1], questions: r[2], ingredients: r[3], dishes: r[4],
          profile: r[5], groups: r[6], rules: r[7], chronic: r[8], source: 'api'
        };
      });
    }).catch(function (e) {
      console.warn('[api] 后端不可用，回落到本地副本：', e && e.message);
      var d = fromLocal();
      d.lastError = e && e.kind ? e : null;
      return d;
    });
  }

  /* 探后端是否活着：{ up, kind, detail } */
  function diagnose() {
    return get(EP.health, 4000).then(function (r) {
      return { up: true, detail: r || {} };
    }).catch(function (e) {
      return { up: false, kind: (e && e.kind) || 'unknown', detail: (e && e.detail) || (e && e.message) || '' };
    });
  }

  global.API = {
    EP: EP,
    get: get,
    post: post,
    loadAll: loadAll,
    diagnose: diagnose,
    isFileProtocol: isFileProtocol,
    apiOrigin: function () { return BASE || (isFileProtocol() ? '（file:// 已自动补为 ' + BASE + '）' : location.origin); },
    defaultOrigin: DEFAULT_ORIGIN,
    generateBanquet: function (payload) { return post(EP.generate, payload); }
  };
})(window);
