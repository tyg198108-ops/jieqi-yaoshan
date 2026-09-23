"""API 网关事件 ⇄ ASGI 适配器（纯标准库实现）。

为什么不用 Mangum
=================
腾讯云 CloudBase 的 Python 云函数会在云端 `pip install -r requirements.txt`。
Mangum 自身很小没问题，但它会拖进来几个传递依赖；一旦云端构建环境网络抖动，
整个部署就失败，排查成本很高。

这个适配器只做一件事：把网关事件翻译成 ASGI scope，跑完 app 再翻译回去。
代码 150 行、零依赖，出问题能直接看明白。

兼容的网关事件字段（各家云服务命名不一，这里都认）：
  method    httpMethod / requestContext.httpMethod
  path      path / requestContext.path
  query     queryString(str) / queryStringParameters(dict) / multiValueQueryStringParameters
  headers   headers (dict[str, str])
  body      body（isBase64Encoded 为真时先 base64 解码）
"""
import asyncio
import base64
import json
from urllib.parse import urlencode


def _decode_body(event):
    body = event.get('body')
    if body is None:
        return b''
    if isinstance(body, (bytes, bytearray)):
        raw = bytes(body)
    else:
        raw = str(body).encode('utf-8')
    if event.get('isBase64Encoded'):
        try:
            raw = base64.b64decode(raw)
        except Exception:
            pass
    return raw


def _query_string(event):
    """统一拼成 bytes 形式的 query_string。

    queryString 是原始串优先（保留了重复参数和编码）；没有再拿字典拼。
    """
    qs = event.get('queryString')
    if qs:
        return qs.encode('utf-8') if isinstance(qs, str) else qs

    params = event.get('multiValueQueryStringParameters')
    if params:
        pairs = []
        for k, vs in params.items():
            for v in (vs if isinstance(vs, list) else [vs]):
                pairs.append((k, '' if v is None else str(v)))
        return urlencode(pairs, doseq=True).encode('utf-8')

    params = event.get('queryStringParameters') or {}
    pairs = [(k, '' if v is None else str(v)) for k, v in params.items()]
    return urlencode(pairs, doseq=True).encode('utf-8') if pairs else b''


def build_scope(event):
    ctx = event.get('requestContext') or {}
    method = (event.get('httpMethod') or ctx.get('httpMethod') or 'GET').upper()
    path = event.get('path') or ctx.get('path') or '/'
    if not path.startswith('/'):
        path = '/' + path

    raw_headers = event.get('headers') or {}
    headers = []
    has_content_type = False
    for k, v in raw_headers.items():
        if not isinstance(v, str):
            v = str(v)
        lk = k.lower()
        if lk == 'content-type':
            has_content_type = True
        headers.append((lk.encode('latin-1'), v.encode('latin-1')))

    return {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1',
        'method': method,
        'scheme': (raw_headers.get('x-forwarded-proto') or 'https'),
        'path': path,
        'raw_path': path.encode('latin-1'),
        'query_string': _query_string(event),
        'root_path': '',
        'headers': headers,
        'client': (ctx.get('sourceIp') or '', 0),
        'server': (raw_headers.get('host') or 'cloudbase', 443),
        '_content_type_present': has_content_type,
    }


async def _call_asgi(app, scope, body):
    sent_start = False
    status = {'code': 500}
    headers = []
    chunks = []

    async def receive():
        nonlocal body
        data, body = body, b''
        return {'type': 'http.request', 'body': data, 'more_body': False}

    async def send(message):
        nonlocal sent_start
        t = message['type']
        if t == 'http.response.start':
            sent_start = True
            status['code'] = message['status']
            headers.extend(message.get('headers') or [])
        elif t == 'http.response.body':
            b = message.get('body')
            if b:
                chunks.append(bytes(b))

    try:
        await app(scope, receive, send)
    except Exception as e:  # 兜底：任何未捕获异常都转成 500 JSON，别让网关报神秘错误
        import traceback
        traceback.print_exc()
        body_out = json.dumps({'detail': f'{type(e).__name__}: {e}'}, ensure_ascii=False)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json; charset=utf-8'},
            'isBase64Encoded': False,
            'body': body_out,
        }

    out = b''.join(chunks)
    resp_headers = {}
    for k, v in headers:
        key = k.decode('latin-1')
        val = v.decode('latin-1')
        # Set-Cookie 不能合并，网关一般要求单个 header 一个值
        if key.lower() == 'set-cookie':
            key = key  # 同名会被覆盖，逐个塞进 map 不现实；网关向下游通常只取一个
        if key.lower() in ('content-length', 'transfer-encoding'):
            continue  # 由网关自行计算
        resp_headers[key] = val

    return {
        'statusCode': status['code'],
        'headers': resp_headers,
        'isBase64Encoded': False,
        'body': out.decode('utf-8', errors='replace'),
    }


def handle(app, event):
    """同步入口：内部用 asyncio.run 起一个干净的 loop 跑完整请求。

    云函数容器可能已经有 loop 在跑，也可能已关闭复用，用 asyncio.run 每次新建
    最省心 —— 我们的请求量级下这点开销可以忽略。
    """
    scope = build_scope(event)
    body = _decode_body(event)

    # Starlette 没有 content-type 时会按空 body 处理 POST；写操作缺失会 400
    if not scope.pop('_content_type_present', False) and scope['method'] in ('POST', 'PUT', 'PATCH'):
        if not body:
            body = b''
        scope['headers'].append((b'content-type', b'application/json'))

    return asyncio.run(_call_asgi(app, scope, body))
