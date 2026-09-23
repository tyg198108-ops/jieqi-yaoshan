/* 角色层：一套引擎、三种外壳。
   显隐与文案差异全部由 product_profile.json 的 feature_matrix 驱动，
   这里不写死任何业务判断——改配置就能改外壳。 */
(function (global) {
  'use strict';

  var STORE_KEY = 'ys_role';

  /* 顺序按 product_profile.json 的 build_order：B → A → C */
  var ROLES = [
    { key: 'B', code: 'B_store', icon: '🏪', name: '餐饮门店', desc: '把药膳做成能卖、能复制、能算账的菜单' },
    { key: 'A', code: 'A_professional', icon: '📗', name: '从业者', desc: '出方案，并且能解释为什么' },
    { key: 'C', code: 'C_family', icon: '🏠', name: '家庭用户', desc: '今天吃什么，怎么买，怎么做' }
  ];

  /* 配置读不到时的兜底矩阵（与 product_profile.json 保持一致） */
  var FALLBACK_MATRIX = {
    engine_rules: { A: 'on', B: 'on', C: 'on' },
    rule_detail_with_source: { A: 'on', B: 'opt', C: 'hide' },
    constitution_test: { A: 'on', B: 'opt', C: 'on' },
    /* 席单按场景出：养生宴 14/16 道、家庭餐 6 道、商务餐 8 道，三角色都给 */
    banquet_by_scene: { A: 'on', B: 'on', C: 'on' },
    family_4_1_1: { A: 'opt', B: 'opt', C: 'on' },
    menu_template_by_term: { A: 'opt', B: 'on', C: 'opt' },
    cost_calculation: { A: 'hide', B: 'on', C: 'opt' },
    purchase_list: { A: 'opt', B: 'on', C: 'on' },
    cooking_sop: { A: 'opt', B: 'on', C: 'on' },
    waiter_script: { A: 'opt', B: 'on', C: 'hide' },
    client_profile: { A: 'on', B: 'opt', C: 'opt' },
    multi_store: { A: 'hide', B: 'on', C: 'hide' },
    ai_explain: { A: 'on', B: 'on', C: 'on' },
    ai_menu_copy: { A: 'opt', B: 'on', C: 'hide' },
    ai_qa: { A: 'on', B: 'opt', C: 'on' }
  };

  function read() {
    try { return global.localStorage.getItem(STORE_KEY); } catch (e) { return null; }
  }

  function write(key) {
    try { global.localStorage.setItem(STORE_KEY, key); } catch (e) { /* 隐私模式忽略 */ }
  }

  function Role(profile) {
    this.profile = profile || null;
    this.matrix = (profile && profile.feature_matrix) || FALLBACK_MATRIX;
    var saved = read();
    var valid = ROLES.some(function (r) { return r.key === saved; });
    this.current = valid ? saved : null; /* null 表示还没选过，首屏弹选择 */
  }

  Role.prototype.list = function () {
    var order = (this.profile && this.profile.build_order) || ['B_store', 'A_professional', 'C_family'];
    var self = this;
    return ROLES.slice().sort(function (a, b) {
      return order.indexOf(a.code) - order.indexOf(b.code);
    }).map(function (r) {
      var u = (self.profile && self.profile.target_users && self.profile.target_users[r.code]) || {};
      return {
        key: r.key, code: r.code, icon: r.icon, name: r.name, desc: r.desc,
        who: u.who || '', tone: u.tone || '', must_have: u.must_have || []
      };
    });
  };

  Role.prototype.info = function () {
    var key = this.current || 'B';
    var found = this.list().filter(function (r) { return r.key === key; })[0];
    return found || this.list()[0];
  };

  Role.prototype.set = function (key) {
    this.current = key;
    write(key);
  };

  /* 能力开关：on / opt / hide / future */
  Role.prototype.can = function (feature) {
    var row = this.matrix[feature];
    if (!row) return 'opt';
    return row[this.current || 'B'] || 'opt';
  };

  Role.prototype.show = function (feature) { return this.can(feature) !== 'hide'; };
  Role.prototype.on = function (feature) { return this.can(feature) === 'on'; };

  /* 角色化文案：同一件事，三种说法 */
  var COPY = {
    home_title: {
      B: '按节气出菜单，一键算清成本',
      A: '出方案，并且说得出依据',
      C: '今天吃什么，我帮你配'
    },
    gen_btn: { B: '🍽️ 生成节气菜单', A: '🍽️ 生成节气宴席', C: '🍲 配今天的四菜一汤' },
    gen_desc: {
      B: '养生宴/家庭/商务 · 可算成本 · 可复制',
      A: '养生宴17道 · 带规则出处',
      C: '四菜一汤一饮 · 附买菜清单'
    },
    ing_btn: { B: '🌿 食材库（含目录归属）', A: '🌿 食材库（性味归经）', C: '🌿 食材库（看得懂版）' },
    ing_desc: { B: '哪些能卖，一查就知道', A: '性味归经、剂量、禁忌', C: '这东西适合谁吃' }
  };

  Role.prototype.copy = function (key) {
    var row = COPY[key];
    if (!row) return '';
    return row[this.current || 'B'] || '';
  };

  global.Role = Role;
  global.ROLE_DEFS = ROLES;
})(window);
