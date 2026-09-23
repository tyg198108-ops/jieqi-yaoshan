from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.solar_terms import router as solar_terms_router
from api.constitutions import router as constitutions_router
from api.ingredients import router as ingredients_router
from api.dishes import router as dishes_router
from api.banquet import router as banquet_router
from api.config import router as config_router

app = FastAPI(title='节气药膳师 · 专业版 API', version='1.0.0')

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
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


# 注册路由
app.include_router(solar_terms_router)
app.include_router(constitutions_router)
app.include_router(ingredients_router)
app.include_router(dishes_router)
app.include_router(banquet_router)
app.include_router(config_router)

# 前端静态文件路径：优先构建产物 frontend/dist，否则回退到项目根目录的单文件版
frontend_dist = os.path.join(os.path.dirname(__file__), '../frontend/dist')
project_root = os.path.join(os.path.dirname(__file__), '..')

if os.path.exists(frontend_dist):
    app.mount('/assets', StaticFiles(directory=os.path.join(frontend_dist, 'assets')), name='assets')

    @app.get('/')
    def index():
        return FileResponse(os.path.join(frontend_dist, 'index.html'))
else:
    # 回退：托管根目录单文件版前端。
    # 注意：index.html 里用 ./app-data.js 相对引用，只挂 / 会导致 /app-data.js 404，
    # 页面能开但数据全空。这里把根目录的静态文件逐个显式暴露。
    @app.get('/')
    def index():
        return FileResponse(os.path.join(project_root, 'index.html'))

    @app.get('/index.html')
    def index_html():
        return FileResponse(os.path.join(project_root, 'index.html'))

    # 本地化的前端依赖（Vue / Element Plus），保证断网可用。
    # 单独挂载子目录而非整个根目录，避免把 backend/ 源码和数据库一并暴露出去。
    vendor_dir = os.path.join(project_root, 'vendor')
    if os.path.exists(vendor_dir):
        app.mount('/vendor', StaticFiles(directory=vendor_dir), name='vendor')

    # P2 前端工程化：拆分后的样式与脚本目录（只挂这两个子目录，不挂整个项目根）
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

@app.get('/api/health')
def health_check():
    return {'status': 'ok', 'message': '节气药膳师API运行正常'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
