import contextvars
import uuid

request_id_context = contextvars.ContextVar("request_id", default="")

def get_request_id() -> str:
    req_id = request_id_context.get()
    if not req_id:
        req_id = str(uuid.uuid4())
        request_id_context.set(req_id)
    return req_id
