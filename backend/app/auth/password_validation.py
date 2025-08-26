# app/auth/password_validation.py
import re
from typing import List
from fastapi import HTTPException, status

def validate_password(password: str) -> None:
    """
    Validate password strength and raise HTTPException if invalid.
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character (!@#$%^&*(),.?":{}|<>)
    - No common weak passwords
    """
    errors: List[str] = []
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for digit
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
    
    # Check for common weak passwords
    weak_passwords = [
        'password', 'password123', '12345678', 'qwerty123', 
        'admin123', 'letmein123', 'welcome123', 'Password1',
        'password1', 'Password123', 'admin1234'
    ]
    
    if password.lower() in [weak.lower() for weak in weak_passwords]:
        errors.append("Password is too common and weak")
    
    # Check for sequential characters
    if has_sequential_chars(password):
        errors.append("Password cannot contain sequential characters (e.g., 123, abc)")
    
    # Check for repeated characters
    if has_repeated_chars(password):
        errors.append("Password cannot contain more than 2 consecutive identical characters")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password validation failed",
                "errors": errors
            }
        )

def has_sequential_chars(password: str, min_length: int = 3) -> bool:
    """Check if password contains sequential characters like 123 or abc"""
    password_lower = password.lower()
    
    for i in range(len(password_lower) - min_length + 1):
        # Check for ascending sequence (abc, 123)
        is_ascending = True
        for j in range(min_length - 1):
            if ord(password_lower[i + j + 1]) != ord(password_lower[i + j]) + 1:
                is_ascending = False
                break
        
        if is_ascending:
            return True
        
        # Check for descending sequence (cba, 321)
        is_descending = True
        for j in range(min_length - 1):
            if ord(password_lower[i + j + 1]) != ord(password_lower[i + j]) - 1:
                is_descending = False
                break
        
        if is_descending:
            return True
    
    return False

def has_repeated_chars(password: str, max_repeated: int = 2) -> bool:
    """Check if password has more than max_repeated consecutive identical characters"""
    if len(password) < max_repeated + 1:
        return False
    
    count = 1
    for i in range(1, len(password)):
        if password[i] == password[i-1]:
            count += 1
            if count > max_repeated:
                return True
        else:
            count = 1
    
    return False

def get_password_requirements() -> dict:
    """Return password requirements for frontend display"""
    return {
        "min_length": 8,
        "requirements": [
            "At least 8 characters long",
            "Contains at least one uppercase letter (A-Z)",
            "Contains at least one lowercase letter (a-z)",
            "Contains at least one digit (0-9)",
            "Contains at least one special character (!@#$%^&*(),.?\":{}|<>)",
            "No common weak passwords",
            "No sequential characters (e.g., 123, abc)",
            "No more than 2 consecutive identical characters"
        ]
    }