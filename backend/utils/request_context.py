"""Per-request ContextVars for log enrichment.

Set during the request lifecycle by middleware and auth dependencies;
read by the logging filter so structured log lines carry request_id,
user_id, and org_id without callers having to thread them through.
"""
from contextvars import ContextVar
from typing import Optional

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
org_id_var: ContextVar[Optional[int]] = ContextVar("org_id", default=None)
route_var: ContextVar[Optional[str]] = ContextVar("route", default=None)


def set_request_id(value: Optional[str]) -> None:
    request_id_var.set(value)


def set_user_id(value: Optional[int]) -> None:
    user_id_var.set(value)


def set_org_id(value: Optional[int]) -> None:
    org_id_var.set(value)


def set_route(value: Optional[str]) -> None:
    route_var.set(value)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


def get_user_id() -> Optional[int]:
    return user_id_var.get()


def get_org_id() -> Optional[int]:
    return org_id_var.get()
