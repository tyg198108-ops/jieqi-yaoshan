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

  /* ---- 后端基址：多候选自动探测 ----
     三种运行环境下，后端地址不一样：
       本地双击 bat   → 同源 '/api'（BASE 为空）
       file:// 打开    → 必须补 http://127.0.0.1:8000
       静态托管上线    → 前端在 xxx.tcloudbaseapp.com，后端在 xxx.service.tcloudbase.com，
                         跨域、不同域名，基址必须从 cloud-config 里取
     做法：按顺序探测每个候选的 /api/health，第一个通的就用它。
     上线时只需改 js/cloud-config.js 的 apiBase，不用动这里。
     手动覆盖优先级最高：localStorage.setItem('YS_API_BASE','http://...') */
  var BASE = '';
  var probing = null;

  function isFileProtocol() {
    try { return !!global.location && global.location.protocol === 'file:'; } catch (e) { return false; }
  }

  function overrideBase() {
    try { return global.localStorage && global.localStorage.getItem('YS_API_BASE'); } catch (e) { return null; }
  }

  function candidates() {
    var ov = overrideBase();
    if (ov) return [String(ov).replace(/\/+$/, '')];
    var list = [];
    if (isFileProtocol()) list.push(DEFAULT_ORIGIN);
    var cfg = global.YS_CLOUD_CONFIG || {};
    if (cfg.apiBase) list.push(String(cfg.apiBase).replace(/\/+$/, ''));
    list.push('');                       // 同源兜底
    return list;
  }

  function ensureBase(force) {
    if (probing && !force) return probing;
    probing = null;
    var list = candidates();
    if (list.length === 1) {
      BASE = list[0];
      probing = Promise.resolve(BASE);
      return probing;
    }
    function go(i) {
      if (i >= list.length) {            // 全都没通：落回同源，错误信息里能看到是哪次失败
        BASE = list[list.length - 1];
        return Promise.resolve(BASE);
      }
      BASE = list[i];
      return request(EP.health, { headers: { Accept: 'application/json' } }, 4000)
        .then(function () { return BASE; }, function () { return go(i + 1); });
    }
    probing = go(0);
    return probing;
  }

  /* 同步预设基址：file:// 双击的场景下不能等到探测结束才拼 URL，
     否则首屏那几个请求的路径会是相对的（/api/health 被解析成 file:///api/health）。 */
  (function presetBase() {
    var list = candidates();
    BASE = list[0] || '';
  })();

  function url(path) { return path.charAt(0) === '/' ? BASE + path : path; }

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
    return ensureBase().then(function () {
      return get(EP.health, 5000);
    }).then(function () {
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
    return ensureBase().then(function () {
      return get(EP.health, 4000);
    }).then(function (r) {
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
    /* 后端地址变了（比如刚启动起来）时用 force=true 重新探测 */
    resetBase: function () { return ensureBase(true); },
    ensureBase: ensureBase,
    apiOrigin: function () { return BASE || (isFileProtocol() ? '（file:// 已自动补为 ' + BASE + '）' : location.origin); },
    defaultOrigin: DEFAULT_ORIGIN,
    generateBanquet: function (payload) { return post(EP.generate, payload); }
  };
})(window);
