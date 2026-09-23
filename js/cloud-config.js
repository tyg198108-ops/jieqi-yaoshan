/* 云开发配置。改这里就能切换环境，不用动业务代码。

   env：云开发环境 ID（控制台 → 环境概览 顶部可见）
   留空或 enabled=false → 网站照常使用，只是「我的方案」功能关闭。
   这一点很重要：云不可用时网站必须还能用，不能整站打不开。 */
window.YS_CLOUD_CONFIG = {
  enabled: true,
  env: 'jieqi-yaoshan-d7gd6ypfscd10299f',
  // 这两处域名要分清，别填混：
  //   webBase   = 静态网站托管的默认域名（页面自己所在的域名，不用手填）
  //   apiBase   = 后端云函数的对外域名（HTTP 访问服务给的域名，必须手填）
  // 本机跑 localhost 时这里可以留 null（走同源 /api），不影响本地开发。
  // 可以写单个字符串，也可以写数组 —— 会按顺序逐个试 /api/health，用第一个通的。
  // 不存在的域名解析会立刻失败，不会拖慢页面。
  apiBase: [
    // 静态网站托管的默认域名。只有当你在「HTTP 访问服务」里把 /api/* 路径
    // 挂到这个域名下时才通；没挂会是 404。
    'https://jieqi-yaoshan-d7gd6ypfscd10299f-1308818540.tcloudbaseapp.com',
    // 「HTTP 访问服务」常见的两种默认域名写法，二选一，总有一个对。
    // 开通后控制台显示哪个，就把另一条删掉。
    'https://jieqi-yaoshan-d7gd6ypfscd10299f.service.tcloudbase.com',
    'https://jieqi-yaoshan-d7gd6ypfscd10299f-1308818540.service.tcloudbase.com'
  ],
  // 集合名，需与控制台里建的一致
  collection: {
    plans: 'user_plans',
    profiles: 'user_profiles'
  }
};
