"""应用工厂：本地开发（uvicorn）与云端（云函数）共用同一个 FastAPI 实例。

两种形态的差异由环境变量 YS_API_ONLY 区分：
  未设（本地）：额外挂载前端静态资源，双击 bat 就能访问 http://127.0.0.1:8000
  设为 1（云端）：只暴露 /api/*，前端交给云开发静态网站托管，各自独立扩缩容
"""
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.solar_terms import router as solar_terms_router
from api.constitutions import router as constitutions_router
from api.ingredients import router as ingredients_router
from api.dishes import router as dishes_router
from api.banquet import router as banquet_router
from api.config import router as config_router

_STARTED_AT = time.time()

APP_VERSION = os.environ.get('YS_VERSION', '2026.09.23g')

# 纯 API 模式：静态资源由云开发静态托管提供，这里不挂
API_ONLY = os.environ.get('YS_API_ONLY') == '1'

# CORS：默认放通（本地后端 + GitHub Pages 预览都能连）。
# 上线后可用 YS_CORS_ORIGINS=https://a.com,https://b.com 收窄。
_cors = os.environ.get('YS_CORS_ORIGINS')
ALLOW_ORIGINS = [o.strip() for o in _cors.split(',') if o.strip()] if _cors else ['*']


def create_app():
    app = FastAPI(title='节气药膳师 · 专业版 API', version=APP_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOW_ORIGINS,
        allow_credentials=(ALLOW_ORIGINS != ['*']),
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # 开发期禁用前端资源缓存：改了 js/css 后浏览器仍拿旧文件是最难排查的一类问题。
    # 只针对自家资源，vendor/（Vue、Element Plus 共 3MB）保持可缓存，否则每次刷新都重下。
    @app.middleware('http')
    async def no_cache_static(request, call_next):
        response = await call_next(request)
        p = request.url.path
        if p == '/' or p == '/index.html' or p.startswith(('/js/', '/css/', '/app-data.js')):
            response.headers['Cache-Control'] = 'no-store, must-revalidate'
        return response

    app.include_router(solar_terms_router)
    app.include_router(constitutions_router)
    app.include_router(ingredients_router)
    app.include_router(dishes_router)
    app.include_router(banquet_router)
    app.include_router(config_router)

    @app.get('/api/health')
    def health_check():
        return {
            'status': 'ok',
            'message': '节气药膳师API运行正常',
            'version': APP_VERSION,
            'mode': 'api-only' if API_ONLY else 'local',
            'uptime': int(time.time() - _STARTED_AT),
        }

    if not API_ONLY:
        _mount_frontend(app)

    return app


def _mount_frontend(app):
    """本地形态：把项目根目录的前端资源挂上去。

    注意：index.html 里用 ./app-data.js 相对引用，只挂 / 会导致 /app-data.js 404，
    页面能开但数据全空。这里把需要的静态资源逐个显式暴露，而不是整个根目录
    —— 后者会把 backend/ 源码和数据库一起暴露出去。
    """
    project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

    @app.get('/')
    def index():
        return FileResponse(os.path.join(project_root, 'index.html'))

    @app.get('/index.html')
    def index_html():
        return FileResponse(os.path.join(project_root, 'index.html'))

    vendor_dir = os.path.join(project_root, 'vendor')
    if os.path.exists(vendor_dir):
        app.mount('/vendor', StaticFiles(directory=vendor_dir), name='vendor')

    for sub, name in (('js', 'js'), ('css', 'css')):
        sub_dir = os.path.join(project_root, sub)
        if os.path.exists(sub_dir):
            app.mount('/' + name, StaticFiles(directory=sub_dir), name=name)

    @app.get('/app-data.js')
    def app_data():
        return FileResponse(os.path.join(project_root, 'app-data.js'),
                            media_type='application/javascript')

    @app.get('/test.html')
    def test_html():
        return FileResponse(os.path.join(project_root, 'test.html'))


app = create_app()

# 保证数据库就绪：本地缺库时自动建，云函数冷启动时 /tmp 是空的也会自动灌。
# 有数据就跳过，不影响正常启动速度。
try:
    from db_bootstrap import bootstrap
    _built = bootstrap()
    if _built:
        print(f"[db] 已从 data/*.json 构建数据库：{_built}")
except Exception as e:  # 构建失败先让服务起来，健康检查会暴露问题
    print(f"[db] 初始化失败：{e}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=os.environ.get('YS_HOST', '127.0.0.1'),
                port=int(os.environ.get('YS_PORT', '8000')))
