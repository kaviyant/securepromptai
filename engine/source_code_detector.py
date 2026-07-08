import re
from typing import Dict, Any

class SourceCodeDetector:
    def __init__(self):
        # 1. Regex signature markers for 13 programming languages
        self.language_rules = {
            "Python": [
                re.compile(r'\bdef\s+\w+\s*\(.*\)\s*:'),
                re.compile(r'\bimport\s+[a-zA-Z_]\w*\b'),
                re.compile(r'\bfrom\s+[a-zA-Z_]\w*\s+import\b'),
                re.compile(r'\belif\s+.*:'),
                re.compile(r'__main__'),
                re.compile(r'\bself\.\w+\b'),
                re.compile(r'\bprint\s*\(.*\)')
            ],
            "Java": [
                re.compile(r'\bpublic\s+class\s+\w+'),
                re.compile(r'\bpublic\s+static\s+void\s+main\b'),
                re.compile(r'\bSystem\.out\.print(ln)?\s*\('),
                re.compile(r'\bimport\s+java\.\w+'),
                re.compile(r'@Override')
            ],
            "JavaScript": [
                re.compile(r'\bconsole\.log\s*\('),
                re.compile(r'\bconst\s+\w+\s*='),
                re.compile(r'\blet\s+\w+\s*='),
                re.compile(r'\bvar\s+\w+\s*='),
                re.compile(r'\bdocument\.getElementById\b'),
                re.compile(r'\bfunction\s+\w+\s*\(.*\)\s*\{'),
                re.compile(r'=>\s*\{')
            ],
            "TypeScript": [
                re.compile(r'\binterface\s+[A-Z]\w*\b'),
                re.compile(r'\btype\s+[A-Z]\w*\s*='),
                re.compile(r'\bpublic\s+constructor\b'),
                re.compile(r':\s*(string|number|boolean|any|void|unknown)\b')
            ],
            "C++": [
                re.compile(r'#include\s*<[a-z]+>'),
                re.compile(r'\bstd::cout\b'),
                re.compile(r'\bstd::endl\b'),
                re.compile(r'\busing\s+namespace\s+std\b')
            ],
            "C": [
                re.compile(r'#include\s*<[a-z]+\.h>'),
                re.compile(r'\bprintf\s*\('),
                re.compile(r'\bscanf\s*\('),
                re.compile(r'\bint\s+main\s*\(.*\)'),
                re.compile(r'\bchar\s*\*\s*\w+')
            ],
            "C#": [
                re.compile(r'\bnamespace\s+\w+'),
                re.compile(r'\bConsole\.WriteLine\s*\('),
                re.compile(r'\busing\s+System\w*'),
                re.compile(r'\bpublic\s+override\b')
            ],
            "Go": [
                re.compile(r'\bfunc\s+\w+\s*\(.*\)\s*.*\{'),
                re.compile(r'\bpackage\s+\w+'),
                re.compile(r'\bimport\s*\(\s*"\w+"'),
                re.compile(r'\bfmt\.Println\s*\('),
                re.compile(r':=')
            ],
            "Rust": [
                re.compile(r'\bfn\s+main\s*\('),
                re.compile(r'\bfn\s+\w+\s*\(.*\)\s*'),
                re.compile(r'\blet\s+mut\s+\w+'),
                re.compile(r'\bprintln!\s*\('),
                re.compile(r'\bmatch\s+\w+\s*\{'),
                re.compile(r'\buse\s+std::')
            ],
            "PHP": [
                re.compile(r'<\?php'),
                re.compile(r'\becho\s+["\']'),
                re.compile(r'\B\$\w+'),
                re.compile(r'\bfunction\s+\w+\s*\(.*\)\s*\{'),
                re.compile(r'\brequire_once\b')
            ],
            "Shell": [
                re.compile(r'#!/bin/[a-z]+'),
                re.compile(r'\becho\s+-e\b'),
                re.compile(r'\bsudo\s+[a-z]+'),
                re.compile(r'\bapt-get\s+install\b'),
                re.compile(r'\bcurl\s+.*-X\b'),
                re.compile(r'\bwget\s+http')
            ],
            "SQL": [
                re.compile(r'\bSELECT\b.*\bFROM\b', re.IGNORECASE | re.DOTALL),
                re.compile(r'\bINSERT\s+INTO\b', re.IGNORECASE),
                re.compile(r'\bUPDATE\b.*\bSET\b', re.IGNORECASE | re.DOTALL),
                re.compile(r'\bDELETE\s+FROM\b', re.IGNORECASE),
                re.compile(r'\bCREATE\s+TABLE\b', re.IGNORECASE),
                re.compile(r'\bALTER\s+TABLE\b', re.IGNORECASE)
            ],
            "HTML": [
                re.compile(r'<!DOCTYPE html>', re.IGNORECASE),
                re.compile(r'<html.*>', re.IGNORECASE),
                re.compile(r'<head.*>', re.IGNORECASE),
                re.compile(r'<body.*>', re.IGNORECASE),
                re.compile(r'<div.*>', re.IGNORECASE),
                re.compile(r'<script.*>', re.IGNORECASE),
                re.compile(r'<link\s+rel=')
            ],
            "CSS": [
                re.compile(r'\bbody\s*\{'),
                re.compile(r'\bmargin\s*:\s*\d'),
                re.compile(r'\bpadding\s*:\s*\d'),
                re.compile(r'\bcolor\s*:\s*#'),
                re.compile(r'\bbackground-color\s*:\s*'),
                re.compile(r'\.[a-zA-Z0-9_-]+\s*\{'),
                re.compile(r'#[a-zA-Z0-9_-]+\s*\{')
            ]
        }

        # 2. Heuristics for credentials inside code lines
        self.code_secret_pattern = re.compile(
            r'\b(pass|password|pwd|key|token|secret|credential|db_pass|auth_key)\s*[:=]\s*["\']([a-zA-Z0-9_\-.~+=@#$%^&*()!]{8,})["\']',
            re.IGNORECASE
        )

    def scan(self, text: str) -> Dict[str, Any]:
        """
        Scans text for source code footprints and detects hardcoded secrets in code.
        """
        scores = {}
        
        # 1. Evaluate densities for each language
        for lang, rules in self.language_rules.items():
            matches_count = 0
            for rule in rules:
                matches_count += len(rule.findall(text))
            if matches_count > 0:
                scores[lang] = matches_count

        # 2. Get winning language
        if not scores:
            return {
                "detected": False,
                "language": None,
                "confidence": 0,
                "severity": "LOW",
                "has_secrets": False
            }

        detected_lang = max(scores, key=scores.get)
        match_density = scores[detected_lang]

        # Calculate Confidence Score (0-100) based on match density
        # 1 match = 40%, 2 matches = 70%, 3+ matches = 95%
        confidence = min(30 * match_density + 10, 98)

        # 3. Check for secrets/credentials inside code
        secrets_found = self.code_secret_pattern.findall(text)
        has_secrets = len(secrets_found) > 0
        
        # Risk assessment: source code leaks are generally HIGH,
        # but CRITICAL if they contain credentials!
        severity = "CRITICAL" if has_secrets else "HIGH"

        return {
            "detected": True,
            "language": detected_lang,
            "confidence": confidence,
            "severity": severity,
            "has_secrets": has_secrets,
            "secrets_count": len(secrets_found)
        }
