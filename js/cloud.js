/* 云开发接入层：登录 + 「我的方案」存取。

设计原则
========
1. **绝不阻断主流程**。SDK 没加载、环境没配、网络不通，全都降级为「功能关闭」，
   网站其余部分照常可用。所以这里每个方法失败都返回 rejected promise 或空结果，
   绝不抛同步异常。
2. **后端不加鉴权**。.Server 侧规则引擎是无状态纯计算，不接触用户数据。
   用户数据走云开发数据库，靠集合权限「仅创建者可读写」隔离，
   比自己写一套 token 校验更不容易出错。
3. **匿名登录打底**。访客打开就有身份，能用「我的方案」；想跨设备同步再绑手机号。
   这样首次使用零门槛（不用注册就能存东西），转化率比强制注册高得多。
*/
(function (global) {
  'use strict';

  var CFG = global.YS_CLOUD_CONFIG || { enabled: false };
  var VERSION = '2026.09.23g';

  var state = {
    enabled: !!CFG.enabled && !!CFG.env,
    ready: false,
    busy: false,
    uid: null,
    loginType: null,   // ANONYMOUS / PHONE / ...
    error: null
  };

  var _app = null, _auth = null, _db = null;
  var _initPromise = null;
  var _sdkPromise = null;

  var SDK_URL = (CFG.sdkUrl || 'https://static.cloudbase.net/cloudbase-js-sdk/2.6.0/cloudbase.full.js');

  function sdk() { return global.cloudbase; }

  function fail(msg) {
    state.error = msg;
    return Promise.reject(new Error(msg));
  }

  /* 动态注入 SDK。
     为什么不用 <script src>：同步阻塞会让首屏卡在 CDN 上，一旦 CDN 慢或被墙，
     整个页面白屏。改成异步注入后，SDK 永远只能影响「我的方案」这一个功能。 */
  function loadSdk(timeoutMs) {
    if (sdk()) return Promise.resolve(true);
    if (_sdkPromise) return _sdkPromise;

    _sdkPromise = new Promise(function (resolve, reject) {
      var el = global.document.createElement('script');
      var done = false;
      function finish(ok, msg) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        ok ? resolve(true) : reject(new Error(msg));
      }
      var timer = setTimeout(function () { finish(false, 'SDK 加载超时'); }, timeoutMs || 8000);
      el.src = SDK_URL;
      el.async = true;
      el.onload = function () { finish(!!sdk(), 'SDK 加载后未注册全局对象'); };
      el.onerror = function () { finish(false, '云开发 SDK 加载失败'); };
      try {
        (global.document.head || global.document.body).appendChild(el);
      } catch (e) {
        finish(false, '无法注入 SDK 脚本');
      }
    });

    // 失败后清掉缓存的 promise，下次再点时还能重试
    return _sdkPromise.catch(function (e) {
      _sdkPromise = null;
      throw e;
    });
  }

  /* ---- 初始化 + 登录 ---- */
  function init() {
    if (!state.enabled) return Promise.resolve(false);
    if (_initPromise) return _initPromise;

    _initPromise = loadSdk().then(function () {
      if (!sdk()) throw new Error('云开发 SDK 未加载');
      _app = sdk().init({ env: CFG.env, region: CFG.region });
      _auth = _app.auth({ persistence: 'local' });   // 记住登录态，刷新不用重新 anonymous
      _db = _app.database();
      return ensureLogin();
    }).then(function () {
      state.ready = true;
      state.error = null;
      return true;
    }).catch(function (e) {
      // 常见失败：环境 ID 写错、没开匿名登录、域名没加白名单
      state.ready = false;
      state.error = friendlyError(e);
      return false;
    });

    return _initPromise;
  }

  function friendlyError(e) {
    var m = (e && (e.message || e.errMsg || e.error_description)) || String(e);
    if (/(-50100[0-9]|not exist|environment)/i.test(m)) return '云环境不可用（环境 ID 可能填错）';
    if (/(domain|白名单|origin|host)/i.test(m)) return '当前域名未加入云开发安全域名白名单';
    if (/(network|timeout|fetch)/i.test(m)) return '云服务连接失败';
    if (/(anonymous|未开启|禁用)/i.test(m)) return '控制台未开启「匿名登录」';
    return String(m).slice(0, 120);
  }

  function ensureLogin() {
    state.busy = true;
    return _auth.getLoginState().then(function (ls) {
      if (ls && ls.user) return ls;
      return _auth.signInAnonymously();
    }).then(function (ls) {
      ls = ls || _auth.currentUser;
      var u = (ls && ls.user) || (ls && ls.uid ? ls : null);
      state.uid = (u && (u.uid || u.openId)) || null;
      state.loginType = (ls && ls.loginType) || 'ANONYMOUS';
      return ls;
    }).then(function (ls) { state.busy = false; return ls; },
            function (e) { state.busy = false; throw e; });
  }

  /* ---- 手机号升级：把匿名身份升级成手机号，跨设备可继续看到自己的方案 ----
     需要控制台开通「手机号登录」+ 短信服务；没开通时调用会失败，UI 里已做隐藏处理。 */
  function sendCode(phone) {
    if (!state.ready) return init().then(function () { return sendCode(phone); });
    return _auth.getVerification({ phoneNumber: phone });
  }

  function bindPhone(verificationId, verificationCode) {
    if (!state.ready) return fail('云服务未就绪');
    return _auth.signInWithPhoneNumber({ verificationId: verificationId, verificationCode: verificationCode })
      .then(function () {
        return ensureLogin().then(function () { return state.uid; });
      });
  }

  /* ---- 方案存取 ---- */
  function _col(name) { return _db.collection((CFG.collection && CFG.collection[name]) || name); }

  function savePlan(plan) {
    if (!state.ready) return fail('云服务未就绪，方案只保留在当前页面');
    var doc = {
      title: plan.title || '未命名席单',
      scene: plan.scene || '',
      sceneName: plan.sceneName || '',
      solarTerm: plan.solarTerm || '',
      constitution: plan.constitution || '',
      headcount: plan.headcount || 0,
      dishCount: (plan.dishes || []).length,
      form: plan.form || null,
      dishes: (plan.dishes || []).map(function (d) {
        return {
          name: d.name, course: d.course, course_name: d.course_name,
          position: d.position, main_ingredients: d.main_ingredients,
          efficacy: d.efficacy_chinese || d.efficacy || '',
          safety_level: d.safety_level || ''
        };
      }),
      summary: {
        concept: plan.design_concept || '',
        structure: plan.structure_text || '',
        shopping: plan.shopping_list || []
      },
      appVersion: VERSION,
      createdAt: Date.now()
    };
    return _col('plans').add(doc).then(function (r) {
      return (r && (r.id || r._id)) || null;
    });
  }

  function listPlans(limit) {
    if (!state.ready) return Promise.resolve([]);
    return _col('plans').orderBy('createdAt', 'desc').limit(limit || 30).get()
      .then(function (r) {
        return (r && r.data) || [];
      }).catch(function () {
        return [];
      });
  }

  function getPlan(id) {
    if (!state.ready) return Promise.resolve(null);
    return _col('plans').doc(id).get().then(function (r) {
      var d = (r && r.data) || null;
      return d && d.length ? d[0] : d;
    }).catch(function () { return null; });
  }

  function removePlan(id) {
    if (!state.ready) return Promise.resolve(false);
    return _col('plans').doc(id).remove().then(function () { return true; }, function () { return false; });
  }

  /* ---- 用户偏好（角色、默认体质）---- */
  function saveProfile(patch) {
    if (!state.ready) return Promise.resolve(false);
    var doc = {};
    Object.keys(patch || {}).forEach(function (k) { doc[k] = patch[k]; });
    doc.updatedAt = Date.now();
    return _col('profiles').where({ _openid: state.uid }).limit(1).get()
      .then(function (r) {
        var existing = r && r.data && r.data[0];
        if (existing && existing._id) return _col('profiles').doc(existing._id).update(doc);
        return _col('profiles').add(doc);
      })
      .then(function () { return true; }, function () { return false; });
  }

  global.YSCloud = {
    VERSION: VERSION,
    state: state,
    init: init,
    savePlan: savePlan,
    listPlans: listPlans,
    getPlan: getPlan,
    removePlan: removePlan,
    saveProfile: saveProfile,
    sendCode: sendCode,
    bindPhone: bindPhone,
    canSave: function () { return state.ready; }
  };
})(window);
