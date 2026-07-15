from typing import Annotated

from fastapi import Request
from fastapi.params import Depends
from fastapi.routing import APIRouter
from loguru import logger
from starlette.datastructures import MultiDict, URL, QueryParams
from starlette.responses import RedirectResponse
from starlette.status import HTTP_302_FOUND

from config import AppConfig
from .dependencies import get_config, get_domain_map
from .utils import get_validated_email

router = APIRouter(include_in_schema=False)


def _redirect_to_aaf(query_params: MultiDict, config: AppConfig):
    query = str(QueryParams(query_params))
    redirect_url = URL(config.aaf_authorize_url).replace(query=query)
    return RedirectResponse(
        url=redirect_url,
        status_code=HTTP_302_FOUND,
        headers={"Cache-Control": "no-store"},
    )


def get_entity_id(screen_name: str, domain_map: dict[str, str]):
    """
    Based on screen name (expected to be an email), return the entity ID for the corresponding AAF provider.
    Returns None if no entity ID can be determined.
    """
    email = get_validated_email(screen_name)
    if email is None:
        return None
    return domain_map.get(email.domain)


@router.get("/authorize")
def authorize_proxy(
    request: Request,
    config: Annotated[AppConfig, Depends(get_config)],
    domain_map: Annotated[dict[str, str] | None, Depends(get_domain_map)],
):
    # NOTE: query_params is a MultiDict, may have multiple values for the same key
    query_params = MultiDict(request.query_params)
    # Remove existing entityID, if present
    query_params.pop("entityID", None)
    screen_name: str | None = query_params.get("screen_name")
    # No screen name provided: redirect to AAF with no entityID
    if screen_name is None:
        return _redirect_to_aaf(query_params, config)
    # No domain_map available: redirect to AAF with no entityID
    if domain_map is None:
        logger.warning("No domain map available, redirecting to AAF without entityID")
        return _redirect_to_aaf(query_params, config)

    entity_id = get_entity_id(screen_name, domain_map)
    if entity_id is None:
        logger.warning(
            f"Couldn't determine entity ID from {screen_name}, redirecting to AAF without entityID"
        )
        return _redirect_to_aaf(query_params, config)
    query_params.append("entityID", entity_id)
    return _redirect_to_aaf(query_params, config)
