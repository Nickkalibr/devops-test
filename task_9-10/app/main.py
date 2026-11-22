import asyncio
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="DevOps test app")

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled by the application",
    ("method", "path", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        path = request.url.path
        if path != "/metrics":
            HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, path).observe(
                time.perf_counter() - started
            )


@app.post("/")
@app.post("/hello")
async def hello(request: Request):
    if request.headers.get("Test") != "Hello":
        return Response(status_code=403)
    return Response(content="Hello, World!", media_type="text/plain")


@app.get("/health", response_class=Response)
async def health():
    try:
        result = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "1",
                "-W",
                "2",
                "77.88.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            ),
            timeout=3,
        )
        return_code = await result.wait()
    except (OSError, asyncio.TimeoutError):
        return Response(content="Unavailable", status_code=503, media_type="text/plain")

    if return_code == 0:
        return Response(content="OK", status_code=200, media_type="text/plain")
    return Response(content="Unavailable", status_code=503, media_type="text/plain")


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
