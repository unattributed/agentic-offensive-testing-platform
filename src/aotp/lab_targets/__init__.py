"""Local lab target profiles for AOTP validation."""

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

__all__ = [
    "JUICE_SHOP_BASE_URL",
    "JUICE_SHOP_CONTAINER_NAME",
    "JUICE_SHOP_IMAGE",
    "JUICE_SHOP_PORT",
    "JuiceShopLocalProfile",
    "JuiceShopProfileError",
    "build_local_juice_shop_wstg_profile",
    "local_juice_shop_profile",
]
