/* 「我的方案」浮层：保存、查看历史、删除、账户状态。

做成浮层而不是新页面，是为了不碰现有路由（app.js 里那套 pushState 薄封装）。
外部只需要调用 YSC.open() / YSC.save(s)，不需要知道里面怎么组织。
*/
(function (global) {
  'use strict';

  var V = global.Vue;

  var ui = V.reactive({
    open: false,
    loading: false,
    saving: false,
    msg: '',
    plans: [],
    tab: 'plans'        // plans / account
  });

  function notify(msg, kind) {
    ui.msg = msg;
    if (global.ElementPlus && global.ElementPlus.ElMessage) {
      global.ElementPlus.ElMessage({ message: msg, type: kind || 'success', duration: 2200 });
    }
    setTimeout(function () { if (ui.msg === msg) ui.msg = ''; }, 2500);
  }

  function open(tab) {
    ui.tab = tab || 'plans';
    ui.open = true;
    refresh();
  }

  function refresh() {
    if (!global.YSCloud || !global.YSCloud.canSave()) {
      return global.YSCloud.init().then(function () {
        ui.loading = false;
        return refresh();
      }).catch(function () { ui.loading = false; });
    }
    ui.loading = true;
    return global.YSCloud.listPlans(30).then(function (list) {
      ui.plans = list || [];
      ui.loading = false;
    }).catch(function (e) {
      ui.loading = false;
      notify('读取失败：' + ((e && e.message) || '未知错误'), 'error');
    });
  }

  /* 保存当前结果。s 是全局状态对象（Vue reactive），banquet 是后端返回的完整结果。 */
  function save(s) {
    if (!s || !s.banquet) { notify('还没有生成结果，先生成再保存', 'warning'); return; }
    var b = s.banquet;
    if (!global.YSCloud.canSave()) {
      notify('正在连接…', 'info');
      return global.YSCloud.init().then(function (ok) {
        if (!ok) {
          notify('云服务暂不可用（' + (global.YSCloud.state.error || '未配置') + '）', 'error');
          return false;
        }
        return save(s);
      });
    }
    ui.saving = true;
    return global.YSCloud.savePlan({
      title: [b.solar_term && b.solar_term.name, b.scene_name, b.structure_label]
        .filter(Boolean).join(' · ') + ' ' + ((b.dishes || []).length) + '道',
      scene: b.banquet_type || '',
      sceneName: b.scene_name || '',
      solarTerm: (b.solar_term || {}).name || '',
      constitution: (b.main_constitution || {}).name || '',
      headcount: b.headcount || 0,
      form: JSON.parse(JSON.stringify(s.form || {})),
      snapshot: JSON.parse(JSON.stringify(b)),
      dishes: (b.dishes || []).map(function (d) { return { name: d.dish && d.dish.name }; })
    }).then(function (id) {
      ui.saving = false;
      notify(id ? '已保存到「我的方案」' : '保存失败', id ? 'success' : 'error');
      refresh();
      return id;
    }).catch(function (e) {
      ui.saving = false;
      notify('保存失败：' + ((e && e.message) || '未知错误'), 'error');
    });
  }

  function viewPlan(p, s) {
    if (!p || !p.snapshot) { notify('这条方案的完整数据不完整，无法还原', 'warning'); return; }
    s.banquet = p.snapshot;
    s.page = 'gen';
    s.genView = 'result';
    ui.open = false;
    notify('已载入该方案', 'success');
  }

  function removePlan(id) {
    return global.YSCloud.removePlan(id).then(function (ok) {
      notify(ok ? '已删除' : '删除失败', ok ? 'success' : 'error');
      refresh();
    });
  }

  var phone = V.reactive({ visible: false, number: '', code: '', vid: '', step: 0, busy: false });

  function sendSms() {
    if (!/^1\d{10}$/.test(phone.number)) { notify('手机号格式不对', 'warning'); return; }
    phone.busy = true;
    global.YSCloud.sendCode('+86' + phone.number).then(function (r) {
      phone.vid = (r && (r.verification_id || r.verificationId)) || '';
      phone.step = 1;
      phone.busy = false;
      notify('验证码已发送', 'success');
    }).catch(function (e) {
      phone.busy = false;
      notify('发送失败：' + ((e && e.message) || '请确认控制台已开通手机号登录与短信服务'), 'error');
    });
  }

  function verifySms() {
    phone.busy = true;
    global.YSCloud.bindPhone(phone.vid, phone.code).then(function () {
      phone.busy = false;
      phone.step = 2;
      notify('绑定成功，换设备也能看到你的方案', 'success');
    }).catch(function (e) {
      phone.busy = false;
      notify('验证失败：' + ((e && e.message) || '验证码可能有误'), 'error');
    });
  }

  global.YSC = {
    ui: ui,
    phone: phone,
    open: open,
    close: function () { ui.open = false; },
    refresh: refresh,
    save: save,
    viewPlan: viewPlan,
    removePlan: removePlan,
    sendSms: sendSms,
    verifySms: verifySms,
    formatTime: function (ts) {
      if (!ts) return '';
      var d = new Date(ts);
      function p(n) { return (n < 10 ? '0' : '') + n; }
      return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
             ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
    }
  };

  /* ---------------- 组件 ---------------- */
  global.CLOUD_PANEL = {
    props: { s: Object },
    template: [
      '<el-dialog v-model="ui.open" :title="\'👤 我的方案 · 共 \'+ui.plans.length+\' 条\'" width="640px">',
      '  <el-tabs v-model="ui.tab">',
      '    <el-tab-pane label="我的方案" name="plans">',
      '      <div v-if="loading" class="sub-note">正在读取…</div>',
      '      <div v-else-if="!ui.plans.length" class="sub-note" style="line-height:1.9">',
      '        还没有保存的方案。<br>生成菜单后，点结果页右上角的「💾 保存方案」即可存到这里。',
      '      </div>',
      '      <div v-else class="plan-list">',
      '        <div v-for="p in ui.plans" :key="p._id" class="plan-item">',
      '          <div class="plan-main">',
      '            <div class="plan-title">{{p.title}}</div>',
      '            <div class="plan-meta">{{p.solarTerm}} · {{p.constitution}} · {{p.headcount}}人席 · {{formatTime(p.createdAt)}}</div>',
      '          </div>',
      '          <div class="plan-ops">',
      '            <el-button size="small" type="primary" @click="view(p)">查看</el-button>',
      '            <el-button size="small" @click="del(p)">删除</el-button>',
      '          </div>',
      '        </div>',
      '      </div>',
      '    </el-tab-pane>',
      '    <el-tab-pane label="账号与隐私" name="account">',
      '      <div style="line-height:1.9;font-size:13px;color:#4b5563">',
      '        <p><b>当前身份：</b>{{loginDesc}}</p>',
      '        <p style="margin-top:10px"><b>匿名登录</b>不需要注册也不会拿到你的手机号，',
      '          只会生成一个随机 ID，用来区分「哪些方案是你存的」。',
      '          缺点是换手机/清浏览器缓存就找不回来。</p>',
      '        <div v-if="!isPhone" style="margin-top:12px">',
      '          <el-button size="small" @click="phone.visible=true" v-if="!phone.visible">绑定手机号</el-button>',
      '          <div v-else>',
      '            <div v-if="phone.step===0" style="display:flex;gap:8px">',
      '              <el-input v-model="phone.number" placeholder="11 位手机号" size="small" style="flex:1"/>',
      '              <el-button size="small" type="primary" :loading="phone.busy" @click="sendSms">发送验证码</el-button>',
      '            </div>',
      '            <div v-else-if="phone.step===1" style="display:flex;gap:8px">',
      '              <el-input v-model="phone.code" placeholder="验证码" size="small" style="flex:1"/>',
      '              <el-button size="small" type="primary" :loading="phone.busy" @click="verifySms">确认绑定</el-button>',
      '            </div>',
      '            <div v-else style="color:#16a34a">✓ 已绑定，换设备用手机号登录即可同步。</div>',
      '          </div>',
      '          <div class="sub-note" style="margin-top:8px">',
      '            需要在控制台开通「手机号登录」与短信服务；未开通时本功能不可用，不影响其余使用。</div>',
      '        </div>',
      '        <div style="margin-top:16px;padding-top:12px;border-top:1px solid #e5e7eb">',
      '          <p><b>隐私说明</b></p>',
      '          <p>我们只保存你主动点击「保存方案」的席单内容，不采集通讯录、相册、位置等任何权限。',
      '          你可在任意时刻删除全部方案，删除后不可恢复。</p>',
      '        </div>',
      '      </div>',
      '    </el-tab-pane>',
      '  </el-tabs>',
      '</el-dialog>'
    ].join(''),
    setup: function (props) {
      var C = global.YSC;
      var s = props.s;
      return {
        ui: C.ui,
        phone: C.phone,
        loading: Vue.computed(function () { return C.ui.loading; }),
        loginDesc: Vue.computed(function () {
          var st = global.YSCloud && global.YSCloud.state;
          if (!st || !st.ready) return '未连接云服务（仍可正常使用，但不能保存方案）';
          return st.loginType === 'PHONE' ? '手机号用户' : '匿名用户（ID 已本地保存）';
        }),
        isPhone: Vue.computed(function () {
          var st = global.YSCloud && global.YSCloud.state;
          return !!(st && st.loginType === 'PHONE');
        }),
        formatTime: C.formatTime,
        view: function (p) { return C.viewPlan(p, s); },
        del: function (p) { return C.removePlan(p._id); },
        sendSms: C.sendSms,
        verifySms: C.verifySms
      };
    }
  };
})(window);
