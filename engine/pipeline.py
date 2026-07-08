from typing import List, Dict, Any
from engine.preprocessing import TextPreprocessor
from engine.regex_detector import RegexDetector
from engine.ner_detector import NerDetector
from engine.ml_detector import MLDetector
from engine.config import CONFIDENCE_THRESHOLD

class DetectionPipeline:
    def __init__(self, model_dir: str = "model"):
        self.regex_detector = RegexDetector()
        self.ner_detector = NerDetector()
        self.ml_detector = MLDetector(model_dir=model_dir)

    def _resolve_overlaps(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates overlapping entity indices.
        If two matched spans overlap, resolves the conflict by:
        1. Prioritizing specific regex entities (e.g. EMAIL) over generic NER (e.g. ORGANIZATION).
        2. Choosing the match with the higher confidence rating.
        """
        # Sort findings by start index ascending, and length descending
        sorted_findings = sorted(
            findings, 
            key=lambda x: (x["start"], -(x["end"] - x["start"]))
        )

        resolved = []
        for current in sorted_findings:
            if not resolved:
                resolved.append(current)
                continue

            last = resolved[-1]
            
            # Check for overlap: current start is before last end
            if current["start"] < last["end"]:
                # We have an overlap! Determine which to keep.
                # Heuristic 1: If one is a generic NER type (NAME, ORGANIZATION, LOCATION, DATE) 
                # and the other is a specific regex type, keep the specific one.
                generic_types = ["NAME", "ORGANIZATION", "LOCATION", "DATE"]
                last_is_generic = last["type"] in generic_types
                current_is_generic = current["type"] in generic_types

                if last_is_generic and not current_is_generic:
                    # Replace last with current
                    resolved[-1] = current
                elif current_is_generic and not last_is_generic:
                    # Keep last, discard current
                    continue
                else:
                    # Heuristic 2: Compare confidence scores
                    if current["confidence"] > last["confidence"]:
                        resolved[-1] = current
                    else:
                        # Keep last
                        continue
            else:
                resolved.append(current)

        return resolved

    def scan(self, raw_text: str) -> Dict[str, Any]:
        """
        Executes the full pipeline:
        1. Preprocesses text (NFKC Normalization + Space compressions).
        2. Scans via heuristics compiled regexes.
        3. Scans via spaCy Named Entity Recognition (NER).
        4. Resolves overlapping tokens.
        5. Computes document ML risk score.
        6. Standardizes findings into JSON scheme.
        """
        if not raw_text or not raw_text.strip():
            return {"detected": False, "entities": []}

        # 1. Preprocess
        clean_text = TextPreprocessor.clean(raw_text)

        # 2. Gather Regex & Checksum matches
        regex_findings = self.regex_detector.scan(clean_text)

        # 3. Gather spaCy NER matches
        ner_findings = self.ner_detector.scan(clean_text)

        # 4. Combine and resolve overlaps
        all_findings = regex_findings + ner_findings
        resolved_findings = self._resolve_overlaps(all_findings)

        # Filter out findings below confidence threshold
        final_entities = []
        for entity in resolved_findings:
            if entity["confidence"] >= CONFIDENCE_THRESHOLD:
                # Format to final requested JSON structure
                final_entities.append({
                    "type": entity["type"],
                    "value": entity["value"],
                    "confidence": entity["confidence"],
                    "severity": entity["severity"]
                })

        # 5. ML Document Classification integration
        # ML evaluates general prompt context. If ML detects high threat and nothing
        # was captured by regex/NER, we can append a general class warning.
        ml_prediction = self.ml_detector.predict(clean_text)
        if ml_prediction["is_sensitive"] and len(final_entities) == 0:
            final_entities.append({
                "type": "SECRET",
                "value": "Context-flagged sensitive content",
                "confidence": ml_prediction["confidence"],
                "severity": "MEDIUM"
            })

        detected = len(final_entities) > 0

        return {
            "detected": detected,
            "entities": final_entities
        }
