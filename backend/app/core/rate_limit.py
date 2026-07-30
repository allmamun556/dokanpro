from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# In-memory backend — correct for this single-process deployment. Would need
# a shared backend (Redis) only if this ever runs multiple backend replicas.
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # Matches the {"detail": "..."} shape every other error in this API
    # already uses, so the frontend doesn't need to special-case 429s.
    return JSONResponse(status_code=429, content={"detail": "Too many requests, please try again shortly"})
