from __future__ import annotations

import re
from typing import Any


DEVICE_ALIASES = {
    "lamp-agent": ("lampe", "lumiere"),
    "plug-agent": ("prise",),
    "thermostat-agent": ("thermostat", "chauffage"),
}

TURN_ON_WORDS = ("allume", "active", "demarre")
TURN_OFF_WORDS = ("eteins", "desactive", "coupe")
STATE_WORDS = ("etat", "status", "statut")
SET_TEMP_WORDS = ("regle", "mets", "fixe")


def normalize(text: str) -> str:
    lowered = text.lower().strip()
    return (
        lowered.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("donne-moi", "donne moi")
    )


def detect_device(text: str) -> str | None:
    normalized = normalize(text)
    for device, aliases in DEVICE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return device
    return None


def parse_user_command(text: str) -> dict[str, Any]:
    normalized = normalize(text)
    device = detect_device(normalized)
    if not device:
        return {
            "ok": False,
            "error": "Objet inconnu. Utilisez lampe, prise ou thermostat.",
        }

    if any(word in normalized for word in TURN_ON_WORDS):
        return {
            "ok": True,
            "target": device,
            "action": "turn_on",
            "parameters": {},
        }

    if any(word in normalized for word in TURN_OFF_WORDS):
        return {
            "ok": True,
            "target": device,
            "action": "turn_off",
            "parameters": {},
        }

    if any(word in normalized for word in STATE_WORDS) or "donne moi" in normalized:
        return {
            "ok": True,
            "target": device,
            "action": "get_state",
            "parameters": {},
        }

    temperature_match = re.search(r"(\d{2})(?:\s*°?\s*c)?", normalized)
    if device == "thermostat-agent" and any(word in normalized for word in SET_TEMP_WORDS) and temperature_match:
        return {
            "ok": True,
            "target": device,
            "action": "set_target_temperature",
            "parameters": {"target_temperature": int(temperature_match.group(1))},
        }

    return {
        "ok": False,
        "error": "Commande non reconnue. Exemples: allume la lampe, eteins la prise, donne-moi l'etat du thermostat.",
    }
