"""Text cleaning utility"""
import re


class TextCleaner:
    """Utility for text cleaning"""
    
    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Remove extra whitespace"""
        return " ".join(text.split())
    
    @staticmethod
    def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
        """Remove special characters"""
        if keep_punctuation:
            pattern = r"[^a-zA-Z0-9\s\.\,\!\?\-]"
        else:
            pattern = r"[^a-zA-Z0-9\s]"
        return re.sub(pattern, "", text)
    
    @staticmethod
    def lowercase(text: str) -> str:
        """Convert to lowercase"""
        return text.lower()
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text with standard cleaning pipeline"""
        text = TextCleaner.remove_extra_whitespace(text)
        text = TextCleaner.lowercase(text)
        return text
