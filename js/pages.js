/* 四个页面组件。模板用字符串（Vue3 全局版带运行时编译器，无需构建步骤）。
   共享状态由根组件以 props.s 传入，页面直接读写 s 上的字段。 */
(function (global) {
  'use strict';

  var PAGES = {};

  /* ---- 生成失败的错误卡片 ----
     原来只甩一句 "生成失败：Failed to fetch"，用户看不出该干什么。
     这里按 kind 给出可执行步骤，并且用 file:// 打开时明确提示换地址。
     probe=true 表示需要再探一次后端，确认是「服务没起」还是「接口报错」。 */
  function errBoxFor(e, backendUp) {
    var kind = (e && e.kind) || 'unknown';
    var fileMode = global.API && global.API.isFileProtocol && global.API.isFileProtocol();
    var origin = (global.API && global.API.apiOrigin && global.API.apiOrigin()) || 'http://127.0.0.1:8000';

    var OPEN_STEPS = [
      '双击项目根目录的 <b>启动节气药膳师.bat</b>',
      '等窗口出现「服务启动中」后，浏览器访问 <b>' + origin + '</b>',
      '回到这里点「重试」'
    ];
    if (fileMode) {
      OPEN_STEPS.unshift('当前是<b>双击 index.html</b> 打开的（地址栏是 file://），请改用上面的网址访问');
    }

    var M = {
      network: {
        icon: '🔌',
        title: '连不上后端服务',
        why: '安全校验依赖后端规则引擎，后端不可用时不产出未校验结果。',
        probe: true,
        steps: OPEN_STEPS
      },
      timeout: {
        icon: '🐢',
        title: '后端响应超时',
        why: '服务接到了请求但 20 秒内没算完，通常是数据库忙或刚启动还在热数据。',
        probe: true,
        steps: OPEN_STEPS.concat(['若反复超时，重启一次服务再试'])
      },
      http: {
        icon: '⚠️',
        title: '后端返回错误 ' + ((e && e.status) || ''),
        why: '服务在跑，但这次生成被拒绝了。',
        probe: false,
        steps: ['点「重试」再来一次', '换一个节气/体质组合试，看是不是特定组合触发的', '仍失败就把下面这行信息截给我']
      },
      parse: {
        icon: '🧩',
        title: '返回内容解析失败',
        why: '后端回了非 JSON 内容，多半是被代理或缓存拦了一道。',
        probe: false,
        steps: ['按 Ctrl+F5 硬刷新页面', '确认没有开着会改写响应的代理/VPN']
      }
    };

    var box = M[kind] || {
      icon: '❓', title: '生成失败',
      why: (e && e.message) || '未知错误',
      probe: true, steps: OPEN_STEPS
    };
    box = JSON.parse(JSON.stringify(box));   // 复制一份，避免改到模板
    box.kind = kind;
    if (e && e.detail) box.detail = e.detail;
    if (backendUp === false) box.steps = OPEN_STEPS;
    return box;
  }

  /* ---------------- 首页 ---------------- */
  PAGES.home = {
    props: { s: Object },
    template: [
      '<div>',
      '  <div class="hero">',
      '    <h1>{{s.curTerm.name}} · {{seasonName(s.curTerm.season)}}<span v-if="s.curTerm.english_name" class="en"> {{s.curTerm.english_name}}</span></h1>',
      '    <div class="sub">{{s.curTerm.date_range}} | 对应脏腑：{{s.curTerm.corresponding_organ}}</div>',
      '    <div class="note">',
      '      <strong>气候特点：</strong>{{s.curTerm.climate_features}}<br>',
      '      <strong>养生原则：</strong>{{s.curTerm.health_principle}}<br>',
      '      <strong>饮食要点：</strong>{{s.curTerm.diet_notes}}',
      '    </div>',
      '    <div style="margin-top:12px;color:#92400e;font-size:14px">{{s.role.copy("home_title")}}</div>',
      '  </div>',
      '  <div class="btn-grid">',
      '    <div class="btn-card" @click="s.page=\'test\'" v-if="s.role.show(\'constitution_test\')">',
      '      <div class="btn-icon">📋</div><div class="btn-title">九种体质测试</div><div class="btn-desc">答题判断体质倾向</div></div>',
      '    <div class="btn-card" @click="s.page=\'gen\'">',
      '      <div class="btn-icon">🍽️</div><div class="btn-title">{{s.role.copy("gen_btn")}}</div><div class="btn-desc">{{s.role.copy("gen_desc")}}</div></div>',
      '    <div class="btn-card" @click="s.page=\'ing\'">',
      '      <div class="btn-icon">🌿</div><div class="btn-title">{{s.role.copy("ing_btn")}}</div><div class="btn-desc">{{s.role.copy("ing_desc")}}</div></div>',
      '  </div>',
      '  <div class="card">',
      '    <h3>📅 二十四节气</h3>',
      '    <el-tabs v-model="s.activeSeason">',
      '      <el-tab-pane v-for="x in [\'春\',\'夏\',\'秋\',\'冬\']" :key="x" :label="x+\'季\'" :name="x">',
      '        <div class="term-grid">',
      '          <div v-for="t in termsOf(x)" :key="t.id" class="term-item"',
      '               :class="{active: t.id===s.form.tid}" @click="selectTerm(t)">{{t.name}}</div>',
      '        </div>',
      '      </el-tab-pane>',
      '    </el-tabs>',
      '  </div>',
      '  <p style="text-align:center;color:#666;margin-top:30px">',
      '    V2.0 · {{s.dataSource==="api"?"后端 API 数据源":"本地副本（后端未连接）"}} ·',
      '    {{s.dishes.length}} 道膳方 · {{s.ingredients.length}} 味食材 · {{s.rules.pair_rules.length}} 条配伍规则',
      '  </p>',
      '</div>'
    ].join(''),
    setup: function (props) {
      var s = props.s;
      return {
        seasonName: function (x) { return ({ 春: '春季', 夏: '夏季', 秋: '秋季', 冬: '冬季' })[x] || x; },
        termsOf: function (x) { return s.terms.filter(function (t) { return t.season === x; }); },
        /* curTerm 是根组件的 computed，跟随 form.tid，这里只改 tid */
        selectTerm: function (t) { s.form.tid = t.id; s.page = 'gen'; }
      };
    }
  };

  /* ---------------- 体质测试 ---------------- */
  PAGES.test = {
    props: { s: Object },
    template: [
      '<div class="card">',
      '  <div class="nav-btn"><el-button @click="s.page=\'home\'">返回首页</el-button></div>',
      '  <h3>📋 九种体质测试</h3>',
      '  <el-steps :active="s.testStep" simple style="margin:20px 0">',
      '    <el-step title="开始"/><el-step title="答题"/><el-step title="结果"/>',
      '  </el-steps>',
      '  <div v-if="s.testStep===0">',
      '    <p style="line-height:1.8;margin:20px 0">共{{s.questions.length}}题，请根据近一年实际情况作答。</p>',
      '    <el-button type="primary" size="large" @click="startTest">开始答题</el-button>',
      '  </div>',
      '  <div v-else-if="s.testStep===1">',
      '    <p style="font-size:16px;margin-bottom:15px">{{s.qIdx+1}}. {{curQ.question_text}}</p>',
      '    <el-radio-group v-model="s.answers[curQ.id]">',
      '      <el-radio v-for="o in curQ.options" :key="o.text" :label="o.score" style="display:block;margin:10px 0">{{o.text}}（{{o.score}}分）</el-radio>',
      '    </el-radio-group>',
      '    <div style="margin-top:20px">',
      '      <el-button v-if="s.qIdx>0" @click="s.qIdx--">上一题</el-button>',
      '      <el-button type="primary" @click="s.qIdx++" v-if="s.qIdx<s.questions.length-1">下一题</el-button>',
      '      <el-button type="success" @click="calcResult" v-else>提交结果</el-button>',
      '    </div>',
      '    <p style="color:#999;margin-top:10px">{{s.qIdx+1}}/{{s.questions.length}}</p>',
      '  </div>',
      '  <div v-else-if="s.testStep===2">',
      '    <div style="text-align:center;padding:10px">',
      '      <h4>您的体质测试结果</h4>',
      '      <h2 style="color:#8B0000;font-size:32px;margin:10px 0">',
      '        {{s.role.current==="C" ? "倾向 "+s.result.main.name : s.result.main.name}}</h2>',
      '      <p v-if="s.result.sub" style="font-size:18px;color:#666">兼夹体质：{{s.result.sub.name}}</p>',
      '      <div style="text-align:left;background:#f9fafb;padding:20px;border-radius:8px;margin:20px 0;line-height:1.8">',
      '        <p><strong>总体特征：</strong>{{s.result.main.overall_feature}}</p>',
      '        <p><strong>食疗原则：</strong>{{s.result.main.diet_principle}}</p>',
      '        <p><strong>推荐食材：</strong>{{s.result.main.recommended_ingredients.join("、")}}</p>',
      '        <p><strong>慎用食材：</strong>{{s.result.main.avoid_ingredients.join("、")}}</p>',
      '      </div>',
      '      <p v-if="s.role.current===\'C\'" class="sub-note">结果为倾向性建议，不作体质诊断；如有不适请咨询执业医师。</p>',
      '      <el-button type="primary" size="large" @click="genFromResult">为该体质配膳</el-button>',
      '    </div>',
      '  </div>',
      '</div>'
    ].join(''),
    setup: function (props) {
      var s = props.s;
      return {
        curQ: Vue.computed(function () { return s.questions[s.qIdx]; }),
        startTest: function () { s.testStep = 1; s.qIdx = 0; s.answers = {}; },
        calcResult: function () {
          var scores = {};
          s.constits.forEach(function (c) { scores[c.id] = 0; });
          s.questions.forEach(function (q) {
            if (s.answers[q.id] !== undefined) scores[q.constitution_id] += s.answers[q.id];
          });
          var sorted = Object.entries(scores).sort(function (a, b) { return b[1] - a[1]; });
          s.result = {
            main: s.constits.filter(function (c) { return c.id === +sorted[0][0]; })[0],
            sub: (sorted[1] && sorted[1][1] >= sorted[0][1] * 0.5)
              ? s.constits.filter(function (c) { return c.id === +sorted[1][0]; })[0] : null
          };
          s.testStep = 2;
        },
        genFromResult: function () { s.form.cid = s.result.main.id; s.page = 'gen'; }
      };
    }
  };

  /* ---------------- 宴席 / 菜单生成 ---------------- */
  PAGES.banquet = {
    props: { s: Object },
    template: [
      '<div class="card">',
      /* 表单视图：回首页 + 有缓存结果时可一键回看 */
      '  <div v-if="!hasResult" class="nav-btn" style="display:flex;justify-content:space-between;align-items:center">',
      '    <el-button @click="s.page=\'home\'">← 返回首页</el-button>',
      '    <el-button v-if="s.banquet" @click="s.nav.showResult()">↩ 查看上次结果</el-button>',
      '  </div>',
      /* 结果视图：吸顶导航条，返回入口固定在左侧最显眼处 */
      '  <div v-else class="result-bar">',
      '    <button type="button" class="back-link" @click="backToGen">← 返回生成</button>',
      '    <span class="crumb">生成席单 › <b>膳食结果</b></span>',
      '    <span style="flex:1"></span>',
      '    <el-button size="small" @click="s.page=\'home\'">首页</el-button>',
      '    <el-button size="small" @click="discard">✕ 放弃结果</el-button>',
      '    <el-button size="small" @click="print">🖨️ 打印/PDF</el-button>',
      '  </div>',
      '  <h3 v-if="!hasResult">{{s.role.copy("gen_btn")}}</h3>',
      /* 后端没连上时提前说清楚，别等用户填完点生成才失败 */
      '  <div v-if="!hasResult && s.dataSource===\'local\'" class="warn-bar">',
      '    ⚠️ 当前<b>未连上后端</b>（数据是本地副本，只能浏览食材库）。生成菜单必须经过后端规则引擎校验，',
      '    请先双击项目根目录的 <b>启动节气药膳师.bat</b>，再访问 <b>http://127.0.0.1:8000</b>。',
      '  </div>',
      '  <div v-if="!hasResult">',
      '    <el-form label-width="100px" style="margin-top:20px">',
      '      <el-form-item label="选择节气">',
      '        <el-select v-model="s.form.tid" style="width:100%">',
      '          <el-option v-for="t in s.terms" :key="t.id" :label="t.name+\'(\'+t.date_range+\')\'" :value="t.id"/></el-select>',
      '      </el-form-item>',
      '      <el-form-item label="主体质">',
      '        <el-select v-model="s.form.cid" style="width:100%">',
      '          <el-option v-for="c in s.constits" :key="c.id" :label="c.name" :value="c.id"/></el-select>',
      '      </el-form-item>',
      '      <el-form-item label="特殊人群">',
      '        <el-select v-model="s.form.group" style="width:100%">',
      '          <el-option v-for="g in s.groups" :key="g.key" :label="g.name" :value="g.key"/></el-select>',
      '      </el-form-item>',
      '      <el-form-item label="慢病参考" v-if="s.role.show(\'client_profile\') && chronicKeys.length">',
      '        <el-checkbox-group v-model="s.form.chronic">',
      '          <el-checkbox v-for="k in chronicKeys" :key="k" :label="k" :value="k"/>',
      '        </el-checkbox-group>',
      '        <div class="sub-note">勾选后附该慢病的饮食宜忌参考（课件第14课），不参与红线裁决</div>',
      '      </el-form-item>',
      '      <el-form-item label="用餐场景">',
      '        <el-radio-group v-model="s.form.type">',
      '          <el-radio value="health">养生宴</el-radio><el-radio value="family">家庭餐</el-radio><el-radio value="business">商务餐</el-radio>',
      '        </el-radio-group>',
      '        <div class="sub-note">{{typeHint}}</div>',
      '      </el-form-item>',
      '      <el-form-item label="席面人数" v-if="s.form.type===\'health\'">',
      '        <el-input-number v-model="s.form.headcount" :min="4" :max="30" :step="2"/>',
      '        <span class="sub-note">按人数给出份量与备餐节奏建议，默认 10 人席</span>',
      '      </el-form-item>',
      '      <el-form-item label="收尾一道" v-if="s.form.type===\'health\'">',
      '        <el-radio-group v-model="s.form.finale">',
      '          <el-radio value="dessert">药膳点心</el-radio><el-radio value="staple">养生主食</el-radio>',
      '        </el-radio-group>',
      '      </el-form-item>',
      '      <el-button type="primary" size="large" @click="generate" :loading="s.loading">{{s.role.copy("gen_btn")}}</el-button>',
      '      <div v-if="s.errBox" class="err-box">',
      '        <div class="err-title">{{s.errBox.icon}} {{s.errBox.title}}</div>',
      '        <div class="err-why">{{s.errBox.why}}</div>',
      '        <ol class="err-steps"><li v-for="(x,i) in s.errBox.steps" :key="i" v-html="x"></li></ol>',
      '        <div v-if="s.errBox.detail" class="err-detail">诊断信息：{{s.errBox.detail}}</div>',
      '        <div class="err-actions">',
      '          <el-button size="small" type="primary" @click="generate" :loading="s.loading">重试</el-button>',
      '          <el-button size="small" @click="recheck" :loading="s.checking">检测后端</el-button>',
      '        </div>',
      '      </div>',
      '      <p v-else-if="s.genError" style="color:#dc2626;margin-top:12px;font-size:13px">{{s.genError}}</p>',
      '    </el-form>',
      '  </div>',
      '  <div v-else>',
      '    <h2 style="text-align:center;color:#8B0000;margin:20px 0">',
      '      {{s.banquet.solar_term.name}} · {{s.banquet.main_constitution.name}} · {{sceneTitle}}',
      '    </h2>',
      '    <div v-if="s.banquet.structure_text" style="text-align:center;color:#6b7280;font-size:13px;margin:-10px 0 14px">',
      '      席面构成：{{s.banquet.structure_text}}｜按 {{s.banquet.headcount}} 人席设计',
      '    </div>',
      /* 席位要求没被满足时明说（菜谱库缺菜），别让用户以为系统已经达标 */
      '    <div v-if="(s.banquet.unmet||[]).length" class="warn-bar" style="background:#fff7ed;border-color:#fdba74;color:#9a3412">',
      '      ⚠️ 本席有 {{s.banquet.unmet.length}} 个席位没配上要求的菜：',
      '      <span v-for="u in s.banquet.unmet" :key="u.seat">{{u.seat}}（需{{u.label}}）</span>。',
      '      当前位置用了其他菜顶上，补一条对应菜谱即可满足。',
      '    </div>',
      '    <div class="concept-box"><strong>💡 设计理念：</strong><br>{{s.banquet.design_concept}}</div>',
      '    <div class="safe-summary">',
      '      <strong>🛡️ 安全校验汇总</strong>（人群：{{s.banquet.group_name}}｜体质：{{s.banquet.main_constitution.name}}｜共 {{shown.length}} 道）',
      '      <div style="margin-top:10px">',
      '        <span class="safe-num safe-block">🚫 禁用 {{s.banquet.stat.block}}</span>',
      '        <span class="safe-num safe-warn">⚠️ 慎用 {{s.banquet.stat.warn}}</span>',
      '        <span class="safe-num safe-tip">💡 提示 {{s.banquet.stat.tip}}</span>',
      '      </div>',
      '      <div v-if="s.banquet.stat.block>0" style="color:#dc2626;margin-top:10px;font-size:13px">本席存在红线级冲突，请务必调整后再出品。</div>',
      '      <div v-else style="color:#059669;margin-top:10px;font-size:13px">本席未触及禁用红线，可按提示调整用量与人群适配。</div>',
      '      <div v-if="s.banquet.course_tip" style="margin-top:12px;padding-top:12px;border-top:1px dashed #d1d5db;font-size:13px;color:#1e40af">',
      '        <strong>📅 疗程建议：</strong>{{s.banquet.course_tip}}',
      '        <span v-if="s.banquet.course_pending" style="color:#9ca3af">（疗程间隔天数暂未设定）</span>',
      '        <div v-if="s.form.chronic.length" style="margin-top:8px;color:#6b7280">慢病参考：{{s.form.chronic.join("、")}}</div>',
      '      </div>',
      '    </div>',
      '    <div v-for="c in chronicCards" :key="c.name" class="chronic-card">',
      '      <b>{{c.name}}（参考）：</b>{{c.principle}}<br>宜：{{c.recommended.join("、")}}｜忌：{{c.avoid.join("、")}}',
      '      <span class="sub-note">出处：{{c.source_lesson}}</span>',
      '    </div>',
      /* 按上菜分组出小标题：冷菜 / 热菜 / 素菜 / 汤 / 主食 / 甜品 / 饮品，
         场景之间的差别一眼看得出来（家庭 6 道、商务 8 道、养生宴 14~16 道） */
      '    <div v-for="grp in courseGroups" :key="grp.course">',
      '      <h3 style="margin:20px 0 10px">{{grp.icon}} {{grp.name}}（{{grp.items.length}}道）</h3>',
      '      <div v-for="d in grp.items" :key="d.position" class="dish-item">',
      '        <div class="dish-name">{{d.position_name}}：{{d.dish.name}}',
      '          <span v-if="d.require_label" class="seat-tag">{{d.require_label}}</span>',
      '          <span v-if="d.course===\'cold\'||d.course===\'hot\'" class="seat-tag gray">{{d.food_tag}}</span>',
      '          <span v-if="d.method" class="seat-tag gray">{{d.method}}</span>',
      '          <span v-if="d.stat.block>0" style="float:right;font-size:12px;color:#dc2626">🚫 含红线冲突</span>',
      '          <span v-else-if="d.stat.warn>0" style="float:right;font-size:12px;color:#f59e0b">⚠️ 需留意</span>',
      '        </div>',
      /* 药膳汤：药材配伍 + 功效；茶饮：季节 / 功效 / 宜忌 */
      '        <div v-if="d.pairing" class="pairing-line"><strong>🌿 药材配伍：</strong>{{d.pairing}}<br>',
      '          <strong>功效：</strong>{{d.dish.efficacy_chinese || "课件未记载该方功效"}}</div>',
      '        <div v-if="d.drink_note" class="pairing-line"><strong>🍵 {{d.drink_note}}</strong></div>',
      '        <div class="dish-meta"><strong>食材：</strong>{{d.ingredients_text}}<br>',
      '          <strong>技法：</strong>{{d.dish.cooking_method}} | <strong>口味：</strong>{{d.dish.flavor}}</div>',
      '        <div class="dish-effect">🌿 养生功效：{{d.dish.efficacy_chinese}}</div>',
      '        <div class="dish-reason">✅ 适配理由：{{d.match_reason}}</div>',
      '        <div v-for="a in visibleAlerts(d)" :key="a.msg" :class="\'alert alert-\'+a.level">',
      '          <span>{{a.icon}}</span>',
      '          <span style="flex:1">{{a.msg}}<span v-if="a.flag" class="alert-flag">{{a.flag}}</span>',
      '            <br v-if="showSrc"><span v-if="showSrc" class="alert-src">出处：{{a.src}}</span></span>',
      '        </div>',
      '      </div>',
      '    </div>',
      '    <div v-if="s.role.show(\'purchase_list\')">',
      '      <h3>🛒 采购清单</h3>',
      '      <div class="sub-note" style="margin:6px 0">按 {{s.banquet.headcount || 10}} 人席备料；菜谱原方用量见上方每道菜的食材明细，实际采购按自家出品标准换算。</div>',
      '      <p style="line-height:2;margin:10px 0">{{s.banquet.shopping_list.join("、")}}</p>',
      '    </div>',
      '    <div v-if="s.role.current===\'B\'">',
      '      <h3>🧾 出品与时间</h3>',
      '      <pre style="white-space:pre-wrap;font-family:inherit;font-size:13px;line-height:1.8">{{s.banquet.time_schedule}}</pre>',
      '    </div>',
      '    <div class="warn-box"><strong>⚠️ 安全提示：</strong>{{disclaimer}}{{s.banquet.group_warning}}</div>',
      /* 结果页底部再放一次入口：长菜单滑到底也能一键回去 */
      '    <div class="result-bar result-bar-bottom">',
      '      <button type="button" class="back-link" @click="backToGen">← 返回生成</button>',
      '      <span class="crumb">{{s.banquet.solar_term.name}} · {{s.banquet.main_constitution.name}} · {{shown.length}} 道</span>',
      '      <span style="flex:1"></span>',
      '      <el-button type="primary" @click="generate" :loading="s.loading">🔄 重新生成</el-button>',
      '    </div>',
      '  </div>',
      '</div>'
    ].join(''),
    setup: function (props) {
      var s = props.s;
      var showSrc = Vue.computed(function () { return s.role.show('rule_detail_with_source'); });
      /* 后端现在会返回 scene_name；老版本结果（本地缓存/降级数据）没有，用这张表兜 */
      var TYPE_NAME = { health: '养生宴', family: '家庭餐', business: '商务餐' };

      /* 是否处于结果视图：有缓存结果 且 视图切到了 result。
         返回生成页只改 genView，banquet 留着，所以表单条件与结果都不会丢。 */
      var hasResult = Vue.computed(function () {
        return !!(s.banquet && s.genView === 'result');
      });

      return {
        showSrc: showSrc,
        hasResult: hasResult,
        /* 一次点击回到生成页：不经过首页，表单里填过的节气/体质/人群/慢病/类型全部保留 */
        backToGen: function () { s.nav.backToGen(false); },
        /* 放弃结果：确认框三个出口都回生成页，区别只在结果缓存留不留 */
        discard: function () {
          var MB = global.ElementPlus && global.ElementPlus.ElMessageBox;
          if (!MB) { s.nav.backToGen(true); return; }
          MB.confirm(
            '返回生成页后，已填条件会原样保留，可直接改条件再生成一次。',
            '返回生成页？',
            {
              distinguishCancelAndClose: true,
              confirmButtonText: '返回生成（保留结果）',
              cancelButtonText: '放弃结果并清空',
              type: 'warning'
            }
          ).then(function () {
            s.nav.backToGen(false);            // 确认：回生成页，结果留缓存
          }).catch(function (action) {
            if (action === 'cancel') s.nav.backToGen(true);   // 放弃：连结果一起清
            else s.nav.backToGen(false);                      // 关闭/遮罩/Esc：同上一种
          });
        },
        chronicKeys: Vue.computed(function () { return Object.keys(s.chronic || {}).filter(function (k) { return k.charAt(0) !== '_'; }); }),
        chronicCards: Vue.computed(function () {
          return (s.form.chronic || []).map(function (k) { return s.chronic[k]; }).filter(Boolean);
        }),
        /* 席单结构完全由后端按场景给出（养生宴 14/16 道、家庭 6 道、商务 8 道）。
           前端不再按 position 裁剪——以前家庭角色固定截 4 道，三个场景就长一个样了。 */
        shown: Vue.computed(function () { return (s.banquet && s.banquet.dishes) || []; }),
        /* 上菜分组：保持席单顺序聚合，冷菜在前、饮品收尾 */
        courseGroups: Vue.computed(function () {
          var list = (s.banquet && s.banquet.dishes) || [];
          var ICON = { cold: '🥗', hot: '🍲', veg: '🥬', soup: '🍜', staple: '🍚', dessert: '🍮', drink: '🍵' };
          var order = [], map = {};
          list.forEach(function (d) {
            var c = d.course || 'hot';
            if (!map[c]) {
              map[c] = { course: c, name: d.course_name || '菜品', icon: ICON[c] || '🍽️', items: [] };
              order.push(c);
            }
            map[c].items.push(d);
          });
          return order.map(function (c) { return map[c]; });
        }),
        /* 场景提示：把每个场景出几道、怎么构成，在选的时候就讲清楚 */
        typeHint: Vue.computed(function () {
          return ({
            health: '养生宴：冷菜 6 道（3 荤 3 素）+ 热菜 8 道（虾 / 鱼 / 牛羊猪 / 鸡 / 蔬菜五类必覆、技法错开）'
                    + ' + 药膳汤 1 道（标药材配伍）+ 点心或主食 1 道 + 茶饮 1 道，共 17 道',
            family: '家庭餐：四菜一汤一饮（两荤两素 + 例汤 + 饮品），共 6 道',
            business: '商务餐：2 道冷菜 + 4 道热菜 + 1 道汤 + 1 道饮品，共 8 道'
          })[s.form.type] || '';
        }),
        sceneTitle: Vue.computed(function () {
          if (!s.banquet) return '';
          var b = s.banquet;
          return (b.scene_name || TYPE_NAME[b.banquet_type] || b.banquet_type) + ' · ' +
                 (b.structure_label || '') + ' ' + ((b.dishes || []).length) + '道';
        }),
        /* C 家庭隐藏剂量与疗程这类专业提示，只保留风险类警示 */
        visibleAlerts: function (d) {
          if (s.role.current !== 'C') return d.alerts;
          return (d.alerts || []).filter(function (a) { return a.level === 'block' || a.level === 'warn'; });
        },
        disclaimer: Vue.computed(function () {
          var p = (s.rules && s.rules.compliance_phrases) || {};
          return p.disclaimer || '本菜单为饮食养生调理建议，不能替代药物治疗，如有疾病请遵医嘱。';
        }),
        typeName: function (t) { return TYPE_NAME[t] || t; },
        print: function () { global.print(); },
        generate: doGenerate,
        recheck: recheck
      };

      /* 生成、自愈、错误翻译写成 setup 内的具名函数而不是返回对象的方法：
         互相调用时直接走闭包，不依赖 this —— 模板事件里的 this 指向不稳，
         曾导致「检测后端」拿不到 generate，点完只清了错误卡片、没重新生成。 */
      function doGenerate() {
        s.loading = true;
        s.genError = '';
        s.errBox = null;
        global.API.generateBanquet({
          solar_term_id: s.form.tid,
          main_constitution_id: s.form.cid,
          secondary_constitution_id: null,
          special_group: s.form.group || 'none',
          banquet_type: s.form.type || 'health',
          banquet_scale: 'standard',
          headcount: s.form.headcount || 10,
          finale: s.form.finale || 'dessert',
          flavor_preference: null
        }).then(function (res) {
          s.banquet = res;
          s.genView = 'result';
          s.loading = false;
        }).catch(function (e) {
          s.loading = false;
          applyErr(e);
        });
      }

      /* 手动检测后端：活着就直接重新生成，没起就刷新提示 */
      function recheck() {
        s.checking = true;
        global.API.diagnose().then(function (r) {
          s.checking = false;
          if (r.up) {
            s.errBox = null;
            s.genError = '';
            doGenerate();
          } else {
            s.errBox = errBoxFor({ kind: 'network' }, false);
            s.errBox.detail = '仍连不上 ' + global.API.apiOrigin() + '（' + (r.kind || '') + '）';
          }
        });
      }

      /* 把 ApiError 翻成一张能照着做的卡片。
         网络类错误会再探一次后端，区分「服务没起」和「接口报错」——处理办法完全不同。 */
      function applyErr(e) {
        var box = errBoxFor(e, null);
        s.errBox = box;
        s.genError = box.title + '：' + box.why;
        if (!box.probe) return;
        global.API.diagnose().then(function (r) {
          if (r.up) {
            s.errBox = {
              icon: '⚠️',
              title: '后端在跑，但生成接口报错',
              why: '服务正常，是这次请求本身出了问题。',
              steps: ['点「重试」再来一次', '重试仍失败就把下面这行信息截给我'],
              detail: (e && e.detail) || (e && e.message) || ''
            };
          } else {
            s.errBox = errBoxFor(e, false);
            s.errBox.detail = '已确认连不上 ' + global.API.apiOrigin();
          }
        });
      }
    }
  };

  /* ---------------- 食材库 ---------------- */
  PAGES.ingredient = {
    props: { s: Object },
    template: [
      '<div class="card">',
      '  <div class="nav-btn"><el-button @click="s.page=\'home\'">← 返回首页</el-button></div>',
      '  <h3>🌿 药食同源食材库</h3>',
      '  <div class="ing-filter">',
      '    <el-input v-model="s.kw" placeholder="搜名称 / 别名 / 分类 / 归经 / 功效 / 适宜体质"',
      '             style="width:320px" clearable/>',
      '    <el-select v-model="s.ingCat" placeholder="全部分类" style="width:150px" clearable>',
      '      <el-option v-for="c in cats" :key="c" :label="c" :value="c"/></el-select>',
      '    <el-radio-group v-model="s.ingKind">',
      '      <el-radio-button value="all">全部</el-radio-button>',
      '      <el-radio-button value="catalog">药食同源</el-radio-button>',
      '      <el-radio-button value="food">普通食品</el-radio-button>',
      '    </el-radio-group>',
      '  </div>',
      '  <div class="ing-count">',
      '    <template v-if="filtering">',
      '      <span>筛出 <b>{{filterIng.length}}</b> / {{s.ingredients.length}} 味</span>',
      '      <el-button link type="primary" style="margin-left:10px" @click="resetFilter">清空条件</el-button>',
      '      <span v-if="!filterIng.length" class="ing-empty">没有匹配项，换个词或点「清空条件」</span>',
      '    </template>',
      '    <span v-else>共 {{s.ingredients.length}} 味食材，可搜名称、别名、归经、功效</span>',
      '  </div>',
      '  <el-table :data="filterIng" border stripe max-height="620px" :empty-text="emptyText" style="width:100%">',
      '    <el-table-column label="名称" width="130">',
      '      <template #default="sc"><b>{{sc.row.name}}</b>',
      '        <div v-if="sc.row.alias" class="sub-note">别名：{{sc.row.alias}}</div></template>',
      '    </el-table-column>',
      '    <el-table-column prop="category" label="分类" width="150"/>',
      '    <el-table-column v-if="s.role.current!==\'C\'" prop="four_natures" label="四气" width="60"/>',
      '    <el-table-column v-if="s.role.current!==\'C\'" label="五味·归经" width="150">',
      '      <template #default="sc">{{(sc.row.five_flavors||[]).join("")}} · {{(sc.row.meridian_tropism||[]).join("、")}}</template>',
      '    </el-table-column>',
      '    <el-table-column prop="efficacy_chinese" label="功效" show-overflow-tooltip/>',
      '    <el-table-column label="目录归属" width="130">',
      '      <template #default="sc">',
      '        <span v-if="sc.row.in_catalog===1" class="cat-yes" :title="sc.row.catalog_official">',
      '          {{batchTag(sc.row.catalog_batch)}}',
      '        </span>',
      '        <span v-else style="color:#9ca3af">普通食品</span>',
      '      </template>',
      '    </el-table-column>',
      '    <el-table-column prop="contraindication" label="禁忌" width="200" show-overflow-tooltip/>',
      '  </el-table>',
      '  <div v-if="!s.ingredients.length" class="warn-box">',
      '    ⚠️ 食材数据为空（0 味）。请确认后端已启动（启动节气药膳师.bat），然后刷新页面。',
      '  </div>',
      '  <p class="sub-note" style="margin-top:10px">',
      '    目录归属按国家卫健委食药物质目录（累计 106 种：2002 年 87 + 2019 年 6 + 2023 年 9 + 2024 年 4）。',
      '    普通食品不适用该目录，标注为「普通食品」；性味归经课件未记载的一律留空，不作补写。',
      '  </p>',
      '  <p class="sub-note">数据源：{{s.dataSource==="api" ? "后端 API" : "本地副本（后端未连接）"}}',
      '    · 共 {{s.ingredients.length}} 味（目录内 {{catalogCount}} 种） · 前端 v2026.09.23d</p>',
      '</div>'
    ].join(''),
    setup: function (props) {
      var s = props.s;

      /* 一条食材参与搜索的全部文本：名称 / 别名 / 分类 / 性味 / 归经 / 功效 / 适宜体质 / 适宜季节 */
      function haystack(i) {
        return [
          i.name, i.alias, i.category,
          (i.four_natures || ''),
          (i.five_flavors || []).join(''),
          (i.meridian_tropism || []).join('、'),
          i.efficacy_chinese, i.contraindication,
          (i.suitable_constitutions || []).join('、'),
          (i.suitable_seasons || []).join('、'),
          /* 目录里的官方名（如「枣（大枣、酸枣、黑枣）」）也要能搜到 */
          i.catalog_official, i.catalog_batch
        ].join(' ');
      }

      /* 目录归属列：显示「药食同源 · 2023」这种，一眼看出是哪一批进的目录 */
      function batchTag(b) {
        var m = /(\d{4})/.exec(String(b || ''));
        return m ? '药食同源 · ' + m[1] : '药食同源';
      }

      var filtering = Vue.computed(function () {
        return !!(s.kw || s.ingCat || (s.ingKind && s.ingKind !== 'all'));
      });

      return {
        filtering: filtering,
        emptyText: Vue.computed(function () {
          return filtering.value ? '没有匹配「' + s.kw + '」的食材，换个词或清空条件' : '暂无数据';
        }),
        cats: Vue.computed(function () {
          var set = {};
          s.ingredients.forEach(function (i) {
            String(i.category || '').split(/[、,，\/]/).forEach(function (c) {
              c = c.trim();
              if (c) set[c] = 1;
            });
          });
          return Object.keys(set).sort();
        }),
        batchTag: batchTag,
        catalogCount: Vue.computed(function () {
          return s.ingredients.filter(function (i) { return i.in_catalog === 1; }).length;
        }),
        resetFilter: function () { s.kw = ''; s.ingCat = ''; s.ingKind = 'all'; },
        filterIng: Vue.computed(function () {
          var kw = String(s.kw || '').trim();
          return s.ingredients.filter(function (i) {
            if (s.ingKind === 'catalog' && i.in_catalog !== 1) return false;
            if (s.ingKind === 'food' && i.in_catalog === 1) return false;
            if (s.ingCat && String(i.category || '').indexOf(s.ingCat) < 0) return false;
            if (!kw) return true;
            return haystack(i).indexOf(kw) >= 0;
          });
        })
      };
    }
  };

  global.PAGES = PAGES;
})(window);
