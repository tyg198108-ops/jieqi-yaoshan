/* 云开发配置。改这里就能切换环境，不用动业务代码。

   env：云开发环境 ID（控制台 → 环境概览 顶部可见）
   留空或 enabled=false → 网站照常使用，只是「我的方案」功能关闭。
   这一点很重要：云不可用时网站必须还能用，不能整站打不开。 */
window.YS_CLOUD_CONFIG = {
  enabled: true,
  env: 'jieqi-yaoshan-d7gd6ypfscd10299f',
  // 后端地址。本地开发不用填（留 null，走同源 /api）；
  // 部署到云开发后，把「HTTP 访问服务」给的域名填进来，例如：
  //   apiBase: 'https://jieqi-yaoshan-1a2b3c.service.tcloudbase.com'
  // 填错会导致静态站连不上后端，页面降级成本地副本（表现为食材数从 207 掉回 195）。
  apiBase: null,
  // 集合名，需与控制台里建的一致
  collection: {
    plans: 'user_plans',
    profiles: 'user_profiles'
  }
};
