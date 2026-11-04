"""The manufacturer behind a MAC address, from the list that ships with Home Assistant."""

from __future__ import annotations

import aiooui


async def async_load() -> None:
    """Load the manufacturer list (once, from disk, no network)."""
    if not aiooui.is_loaded():
        await aiooui.async_load()


def is_private_mac(mac: str) -> bool:
    """Whether the address is a randomised one (the "locally administered" bit is set)."""
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except ValueError:
        return False


def vendor_of(mac: str) -> str | None:
    """The manufacturer of a MAC address; None if there is none or the list is not loaded.

    A private address (phones randomise theirs) belongs to no manufacturer.
    """
    if not aiooui.is_loaded() or is_private_mac(mac):
        return None
    return aiooui.get_vendor(mac)
