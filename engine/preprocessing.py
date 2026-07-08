import unicodedata
import re

class TextPreprocessor:
    @staticmethod
    def normalize_spaces(text: str) -> str:
        """
        Compresses multiple spaces or tabs into a single space,
        retaining basic newline layout structures.
        """
        # Compress multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize double newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Converts text using NFKC normalization to standard compatibility forms.
        """
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text)

    @classmethod
    def clean(cls, text: str) -> str:
        """
        Full text preprocessing pipeline for cleaning input prompts.
        """
        if not text:
            return ""
        
        # 1. Unicode Normalization
        text = cls.normalize_unicode(text)
        
        # 2. Spaces Normalization
        text = cls.normalize_spaces(text)
        
        return text.strip()
