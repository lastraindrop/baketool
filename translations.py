"""Translation data loading for BakeNexus.

Loads the translations.json file and converts it into the format expected
by Blender's translation system for UI internationalization.
"""

import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_translations():
    """
    Load translations from translations.json in the same directory.
    Returns a dictionary formatted for bpy.app.translations.register.
    Format: {locale: {src_key: translated_str, ...}}
    """
    json_path = Path(__file__).parent / "translations.json"
    if not json_path.exists():
        logger.warning(f"Translation file not found at: {json_path}")
        return {}

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load translations.json: {e}")
        return {}

    # Blender expects: {locale: { (context, src): dest, ... } }
    # Our JSON is: { src: { locale: dest, ... } }

    translations_map = {}

    raw_data = data.get("data", {})

    for src_text, locales in raw_data.items():
        for locale, dest_text in locales.items():
            if locale not in translations_map:
                translations_map[locale] = {}

            # Register for all contexts ("*") and Operator context as fallback
            # Blender uses ("*", src) for general UI
            translations_map[locale][("*", src_text)] = dest_text
            translations_map[locale][("Operator", src_text)] = dest_text

    # Blender renamed the Simplified Chinese locale from zh_CN (<= 4.1) to
    # zh_HANS (4.2+). Register both codes from the single zh_HANS source so
    # extension installs on 4.2+ and legacy source installs both resolve.
    zh_data = translations_map.get("zh_HANS")
    if zh_data:
        translations_map.setdefault("zh_CN", dict(zh_data))

    return translations_map

# Load on module import
translation_data = load_translations()

# Expose the full dictionary for registration
# Format: {locale: {(context, src): dest}}
translation_dict = translation_data
