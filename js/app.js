/* 根组件：加载数据 → 建立角色层 → 挂载四个页面。
   数据一律来自 API.loadAll()（后端优先、本地副本降级）。 */
(function (global) {
  'use strict';

  var SEASON_OF = { 春: '春季', 夏: '夏季', 秋: '秋季', 冬: '冬季' };

  function boot() {
    global.API.loadAll().then(function (d) {
      var role = new global.Role(d.profile);

      var state = Vue.reactive({
        page: 'home',
        loading: false,
        checking: false,
        genError: '',
        errBox: null,
        dataSource: d.source,
        terms: d.terms,
        constits: d.constits,
        questions: d.questions,
        ingredients: d.ingredients,
        dishes: d.dishes,
        groups: d.groups,
        rules: d.rules,
        chronic: d.chronic,
        activeSeason: '秋',
        kw: '',
        ingCat: '',
        ingKind: 'all',
        testStep: 0,
        qIdx: 0,
        answers: {},
        result: null,
        banquet: null,
        /* 生成页的两种视图：'form' 填条件 / 'result' 看结果。
           结果页与生成页共用一个组件，靠它区分；banquet 保留为结果缓存，
           切回表单不清除，浏览器「前进」可直接还原上次结果，不必重算。 */
        genView: 'form',
        /* type 场景：health 养生宴 / family 家庭餐 / business 商务餐
           headcount 宴席人数（养生宴，默认 10 人席）；finale 收尾一道：点心 / 主食 */
        form: { tid: null, cid: 1, group: 'none', type: 'health', scale: 'standard',
                headcount: 10, finale: 'dessert', chronic: [] },
        role: role,
        roleKey: role.current || '',
        showRolePicker: !role.current
      });

      /* 当前节气默认取秋分（order=16）；取不到就取第一条 */
      var def = d.terms.filter(function (t) { return t.order === 16; })[0] || d.terms[0];
      state.form.tid = def ? def.id : 1;
      state.form.cid = (d.constits[0] || {}).id || 1;

      /* ---------------- 导航历史 ----------------
         目的：让「结果页 → 生成页」的按钮与浏览器后退走同一条路，
         点按钮不产生多余历史条目，按后退也不会跳到首页。
         只做一层薄封装，其余页面原先的 s.page 赋值方式完全不变。 */
      var HIST_OK = !!(global.history && global.history.pushState);
      var suppress = false;       // popstate 触发的变更不再回写历史
      var pendingClear = false;   // 后退落地后再清空结果缓存

      var VIEWS = ['home', 'test', 'gen', 'ing'];

      function viewKey() {
        var k = state.page;
        if (k === 'gen' && state.banquet && state.genView === 'result') k += ':result';
        return k;
      }
      function pushView(replace) {
        if (!HIST_OK) return;
        var k = viewKey();
        try {
          if (replace) global.history.replaceState({ ys: k }, '', '#/' + k);
          else global.history.pushState({ ys: k }, '', '#/' + k);
        } catch (e) { /* file:// 下部分浏览器禁止改写地址，忽略即可 */ }
      }
      function applyView(k) {
        var parts = String(k || 'home').split(':');
        var p = parts[0];
        if (VIEWS.indexOf(p) < 0) p = 'home';
        state.page = p;
        if (p === 'gen') state.genView = (parts[1] === 'result' && state.banquet) ? 'result' : 'form';
      }
      global.addEventListener('popstate', function (ev) {
        suppress = true;
        if (pendingClear) { pendingClear = false; state.banquet = null; }
        applyView((ev.state && ev.state.ys) || '');
        Vue.nextTick(function () { suppress = false; });
      });

      /* 结果页 → 生成页的统一出口 */
      state.nav = {
        /* clear=true：连同结果缓存一起清掉 */
        backToGen: function (clear) {
          var st = global.history && global.history.state;
          if (clear) pendingClear = true;
          if (st && st.ys === 'gen:result' && HIST_OK) {
            global.history.back();               // popstate → applyView('gen')
          } else {
            if (clear) state.banquet = null;
            state.genView = 'form';              // history 不可用时直接切
          }
        },
        /* 表单页 → 结果页（复用缓存，不重新请求后端） */
        showResult: function () {
          if (!state.banquet) return;
          state.page = 'gen';
          state.genView = 'result';
        }
      };

      Vue.watch(function () { return state.page; }, function (p, old) {
        if (suppress) return;
        /* 离开生成页就收起结果视图：下次再进来落在表单，不会甩出去旧结果。
           只在「离开」时收，不在「进入」时收——否则会覆盖掉显式跳结果的操作。 */
        if (old === 'gen' && p !== 'gen') state.genView = 'form';
      });
      Vue.watch(viewKey, function () {
        if (suppress) return;
        pushView(false);
      });
      pushView(true);   // 首屏只替换当前条目，不额外留一条历史

      var curTerm = Vue.computed(function () {
        return d.terms.filter(function (t) { return t.id === state.form.tid; })[0] || def || {};
      });
      /* reactive 对象内的 ref 会自动解包，页面里可以直接 s.curTerm.name */
      state.curTerm = curTerm;
      var roleInfo = Vue.computed(function () { return state.role.info(); });
      var compMap = { home: 'page-home', test: 'page-test', gen: 'page-banquet', ing: 'page-ingredient' };
      var currentComp = Vue.computed(function () { return compMap[state.page] || 'page-home'; });

      var app = Vue.createApp({
        setup: function () {
          Vue.watch(function () { return state.roleKey; }, function (v) { state.role.current = v || null; });
          return {
            s: state,
            curTerm: curTerm,
            roleInfo: roleInfo,
            currentComp: currentComp,
            seasonName: function (x) { return SEASON_OF[x] || x; },
            pickRole: function (key) {
              state.role.set(key);
              state.roleKey = key;
              state.showRolePicker = false;
              state.banquet = null;
              state.genView = 'form';
              /* 家庭用户默认落在家庭餐（四菜一汤一饮），门店与从业者默认养生宴 */
              state.form.type = (key === 'C') ? 'family' : 'health';
            },
            roles: Vue.computed(function () { return state.role.list(); })
          };
        }
      });

      app.component('page-home', global.PAGES.home);
      app.component('page-test', global.PAGES.test);
      app.component('page-banquet', global.PAGES.banquet);
      app.component('page-ingredient', global.PAGES.ingredient);

      app.use(global.ElementPlus);
      app.mount('#app');

      global.__state = state;
    }).catch(function (e) {
      document.getElementById('app').innerHTML =
        '<div class="card"><h3>数据加载失败</h3><p style="line-height:1.8;margin-top:10px">' +
        e.message + '</p><p style="margin-top:10px;color:#666">请先启动后端（启动节气药膳师.bat），或确认 app-data.js 存在。</p></div>';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
