from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.application.errors import ApplicationError
from src.bootstrap.container import get_settings
from src.bootstrap.storage import get_storage_dir
from src.presentation.api.alerts import alerts_router
from src.presentation.api.files import files_router
from src.presentation.api.middleware import (
    RequestIdMiddleware,
    application_error_handler,
    fallback_exception_handler,
    http_exception_handler,
    validation_error_handler,
)


STORAGE_DIR = get_storage_dir(get_settings())

app = FastAPI()

# Add RequestIdMiddleware as first middleware (before CORS)
app.add_middleware(RequestIdMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://localhost:3007",
        "http://127.0.0.1:3007",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(ApplicationError, application_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, fallback_exception_handler)

app.include_router(files_router)
app.include_router(alerts_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
