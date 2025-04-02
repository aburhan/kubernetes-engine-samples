import os
from datetime import datetime, timedelta, timezone
import google.auth
import google.auth.transport.requests
from config import METRICS_SCOPE, DEFAULT_EXCLUDED_NAMESPACES, DEFAULT_INCLUDED_K8S_OBJECTS


def get_auth_token():
    """
    Authenticates with Google Cloud using the default service account
    and returns an access token.
    """
    try:
        credentials, _ = google.auth.default(scopes=[METRICS_SCOPE])
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        return credentials.token
    except Exception as e:
        raise RuntimeError(f"Error getting authentication token: {e}")


def get_time_interval(seconds_ago: int) -> tuple[str, str]:
    """
    Returns start and end time in UTC ISO format.
    """
    now_utc = datetime.now(timezone.utc)
    start_time_utc = now_utc - timedelta(seconds=seconds_ago)
    return start_time_utc.isoformat(), now_utc.isoformat()


def build_namespace_filter(env_excluded_var="EXCLUDED_NS", env_included_var="INCLUDED_NS"):
    """
    Builds a filter to exclude and include namespaces.
    """
    excluded_ns = os.getenv(env_excluded_var, "").split(",")
    included_ns = os.getenv(env_included_var, "").split(",")

    usr_excluded_ns = [ns.strip() for ns in excluded_ns if ns.strip()]
    excluded_ns = set(DEFAULT_EXCLUDED_NAMESPACES+ usr_excluded_ns)

    included_ns = [ns.strip() for ns in included_ns if ns.strip()]

    excluded_filter = " AND ".join(
        f'resource.label.namespace_name != "{ns}"' for ns in excluded_ns)
    included_filter = " OR ".join(
        f'resource.label.namespace_name = "{ns}"' for ns in included_ns)

    if excluded_filter and included_filter:
        return f"({excluded_filter}) AND ({included_filter})"
    return excluded_filter or included_filter


def build_included_objects_filter(env_var_name="INCLUDED_OBJECTS"):
    """
    Builds a filter to include specified K8s object types.
    """
    included_objects = os.getenv(env_var_name, "").split(",")
    included_objects = [obj.strip() for obj in included_objects if obj.strip()]

    all_objects = set(DEFAULT_INCLUDED_K8S_OBJECTS + included_objects)
    if not all_objects:
        return ""

    return " OR ".join(
        f'metadata.system_labels."top_level_controller_type" = "{obj}"' for obj in all_objects)
