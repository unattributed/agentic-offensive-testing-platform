"""Local lab target profiles for AOTP validation."""

from .crapi import (
    CRAPI_BASE_URL,
    CRAPI_MAILHOG_URL,
    CRAPI_PROJECT_NAME,
    CRAPI_WEB_PORT,
    CapiLocalProfile,
    CapiProfileError,
    build_local_crapi_wstg_profile,
    local_crapi_profile,
)
from .juice_shop import (
    JUICE_SHOP_BASE_URL,
    JUICE_SHOP_CONTAINER_NAME,
    JUICE_SHOP_IMAGE,
    JUICE_SHOP_PORT,
    JuiceShopLocalProfile,
    JuiceShopProfileError,
    build_local_juice_shop_wstg_profile,
    local_juice_shop_profile,
)
from .registry import (
    LocalTargetRegistryEntry,
    build_local_target_registry,
    get_local_target_entry,
    implemented_local_target_aliases,
)

__all__ = [
    "CRAPI_BASE_URL",
    "CRAPI_MAILHOG_URL",
    "CRAPI_PROJECT_NAME",
    "CRAPI_WEB_PORT",
    "CapiLocalProfile",
    "CapiProfileError",
    "JUICE_SHOP_BASE_URL",
    "JUICE_SHOP_CONTAINER_NAME",
    "JUICE_SHOP_IMAGE",
    "JUICE_SHOP_PORT",
    "JuiceShopLocalProfile",
    "JuiceShopProfileError",
    "LocalTargetRegistryEntry",
    "build_local_crapi_wstg_profile",
    "build_local_juice_shop_wstg_profile",
    "build_local_target_registry",
    "get_local_target_entry",
    "implemented_local_target_aliases",
    "local_crapi_profile",
    "local_juice_shop_profile",
]
