from typing import List, Dict, Any, Tuple

class PromptSanitizer:
    @staticmethod
    def sanitize(
        text: str, 
        entities: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, str]]:
        """
        Replaces sensitive text matches with sequential index placeholders (e.g. [EMAIL_1], [NAME_1]).
        Identical raw values map to the exact same placeholder key.
        Returns the sanitized text and a de-anonymization map.
        """
        if not text or not entities:
            return text, {}

        # 1. Sort entities by start index in descending order
        # Doing replacements from back-to-front prevents character shifts from breaking offset indices!
        sorted_entities = sorted(entities, key=lambda x: x.get("start", 0), reverse=True)
        
        # Track placeholders: Type -> { Raw Value -> Placeholder }
        placeholders_registry: Dict[str, Dict[str, str]] = {}
        # Track counters: Type -> Count
        type_counters: Dict[str, int] = {}
        
        # Output de-anonymization map: Placeholder -> Raw Value
        restore_map: Dict[str, str] = {}
        
        sanitized_chars = list(text)

        # 2. Iterate and replace
        for ent in sorted_entities:
            ent_type = ent["type"]
            # Fallback values if pipeline returned direct list instead of raw indices
            start = ent.get("start")
            end = ent.get("end")
            val = ent.get("value")
            
            if start is None or end is None or not val:
                continue

            # Check if this type has already been registered
            if ent_type not in placeholders_registry:
                placeholders_registry[ent_type] = {}
                type_counters[ent_type] = 0

            # If this specific raw value has already been replaced in the text,
            # re-use the exact same placeholder key
            if val in placeholders_registry[ent_type]:
                placeholder = placeholders_registry[ent_type][val]
            else:
                type_counters[ent_type] += 1
                idx = type_counters[ent_type]
                placeholder = f"[{ent_type}_{idx}]"
                placeholders_registry[ent_type][val] = placeholder
                restore_map[placeholder] = val

            # Replace the string slice with the placeholder
            sanitized_chars[start:end] = list(placeholder)

        sanitized_text = "".join(sanitized_chars)
        return sanitized_text, restore_map

    @staticmethod
    def restore(sanitized_text: str, restore_map: Dict[str, str]) -> str:
        """
        Replaces placeholders with original values.
        """
        restored_text = sanitized_text
        for placeholder, original in restore_map.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text
