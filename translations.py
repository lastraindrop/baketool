import bpy
import json
import os
import logging

logger = logging.getLogger(__name__)

def load_translations():
    """
    Load translations from translations.json in the same directory.
    Returns a dictionary formatted for bpy.app.translations.register.
    Format: {locale: {src_key: translated_str, ...}}
    """
    json_path = os.path.join(os.path.dirname(__file__), "translations.json")
    if not os.path.exists(json_path):
        logger.warning(f"Translation file not found at: {json_path}")
        return {}

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
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

    return translations_map

# Load on module import
translation_data = load_translations()

# Expose the full dictionary for registration
# Format: {locale: {(context, src): dest}}
translation_dict = translation_data