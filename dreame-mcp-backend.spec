# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['run_server.py'],
    pathex=['src'],
    datas=[('src/dreame_mcp/skills', 'dreame_mcp/skills')],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'paho.mqtt',
        'paho.mqtt.client',
        'Crypto',
        'Crypto.Cipher',
        'Crypto.Util',
        'zeroconf',
        'miio',
    ],
    excludes=['tkinter', 'setuptools', 'pip', 'wheel', 'test', 'tests', 'unittest'],
    noarchive=True,
)
# Strip .dist-info but preserve metadata for packages that need it at runtime
_keep_dist = ['fastmcp-', 'mcp-', 'prefab_ui-', 'opentelemetry-', 'email_validator-']
_saved = [e for e in a.datas if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and '.dist-info' in str(e[0])]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and '.dist-info' in str(e[0]))]
a.datas.extend(_saved)
SKIP = ['torch', 'playwright', 'bitsandbytes', 'llvmlite', 'pyarrow', 'pymupdf', 'grpc', 'numba', 'Cython', 'google', 'azure', 'boto3', 'botocore', 'matplotlib', 'pandas', 'scipy', 'sklearn', 'onnxruntime']
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='dreame-mcp-backend',
    debug=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
