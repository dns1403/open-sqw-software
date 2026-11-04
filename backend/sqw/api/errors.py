"""Stable presentation error codes; the numerical core stays language-neutral."""
from fastapi.responses import JSONResponse


class RequestProblem(ValueError):
    def __init__(self, code: str, detail: str, **params):
        super().__init__(detail)
        self.code = code
        self.params = params


def client_error(error: Exception) -> JSONResponse:
    """Keep the original English detail for existing API consumers."""
    return JSONResponse(status_code=422, content={
        "detail": str(error),
        "code": error.code if isinstance(error, RequestProblem) else "invalid_experiment",
        "params": error.params if isinstance(error, RequestProblem) else {},
    })


def validation_issue(error: dict) -> dict:
    """Convert Pydantic diagnostics without exposing malformed input values."""
    kind = error["type"]
    context = error.get("ctx") or {}
    params = {}
    if kind in {"int_type", "int_parsing", "int_from_float"}:
        code = "integer"
    elif kind in {"float_type", "float_parsing", "finite_number"}:
        code = "finite_number"
    elif kind == "greater_than_equal":
        code, params = "minimum", {"minimum": context["ge"]}
    elif kind == "less_than_equal":
        code, params = "maximum", {"maximum": context["le"]}
    elif kind == "missing":
        code = "required"
    elif kind == "extra_forbidden":
        code = "unexpected_field"
    elif kind == "literal_error":
        code = "unsupported_value"
    elif kind in {"json_invalid", "json_type"}:
        code = "invalid_json"
    elif kind in {"list_type", "tuple_type", "dict_type", "model_type", "model_attributes_type", "too_long", "too_short"}:
        code = "invalid_structure"
    else:
        code = "invalid"
    return {"path": list(error["loc"]), "code": code, "params": params}
