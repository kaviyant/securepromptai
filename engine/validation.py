# SecurePrompt AI - Data Validation Checksums

# Verhoeff Algorithm multiplication and permutation matrices (Aadhaar cards validation)
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 5, 8, 2]
]

class DataValidator:
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        """
        Validates Credit Card numbers using Luhn's algorithm.
        """
        digits = [int(d) for d in card_number if d.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                checksum += doubled if doubled < 10 else doubled - 9
            else:
                checksum += digit
        return checksum % 10 == 0

    @staticmethod
    def verhoeff_check(number_str: str) -> bool:
        """
        Validates Aadhaar Card numbers using the Verhoeff algorithm.
        """
        # Strip spacing and filter digits
        digits = [int(d) for d in number_str if d.isdigit()]
        if len(digits) != 12:
            return False
            
        c = 0
        for i, digit in enumerate(reversed(digits)):
            c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]]
        return c == 0

    @staticmethod
    def iban_check(iban: str) -> bool:
        """
        Validates International Bank Account Numbers (IBAN) using the Modulo 97-10 algorithm.
        """
        # Clean formatting
        clean_iban = iban.replace(" ", "").upper()
        if len(clean_iban) < 4:
            return False
            
        # Re-arrange: move first 4 chars to the end
        rearranged = clean_iban[4:] + clean_iban[:4]
        
        # Convert letters to digits (A=10, B=11... Z=35)
        converted_digits = []
        for char in rearranged:
            if char.isalpha():
                converted_digits.append(str(ord(char) - ord('A') + 10))
            elif char.isdigit():
                converted_digits.append(char)
            else:
                return False
                
        number_str = "".join(converted_digits)
        try:
            return int(number_str) % 97 == 1
        except ValueError:
            return False
