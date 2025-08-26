// lib/widgets/password_requirements_widget.dart
import 'package:flutter/material.dart';

class PasswordRequirementsWidget extends StatelessWidget {
  final String password;
  final bool showAll;

  const PasswordRequirementsWidget({
    super.key,
    required this.password,
    this.showAll = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    final requirements = [
      _PasswordRequirement(
        text: 'At least 8 characters long',
        isMet: password.length >= 8,
      ),
      _PasswordRequirement(
        text: 'Contains uppercase letter (A-Z)',
        isMet: _hasUppercase(password),
      ),
      _PasswordRequirement(
        text: 'Contains lowercase letter (a-z)',
        isMet: _hasLowercase(password),
      ),
      _PasswordRequirement(
        text: 'Contains at least one digit (0-9)',
        isMet: _hasDigit(password),
      ),
      _PasswordRequirement(
        text: 'Contains special character (!@#\$%^&*(),.?":{}|<>)',
        isMet: _hasSpecialChar(password),
      ),
      _PasswordRequirement(
        text: 'No common weak passwords',
        isMet: !_isWeakPassword(password),
      ),
      _PasswordRequirement(
        text: 'No sequential characters (e.g., 123, abc)',
        isMet: !_hasSequentialChars(password),
      ),
      _PasswordRequirement(
        text: 'No more than 2 consecutive identical characters',
        isMet: !_hasRepeatedChars(password),
      ),
    ];

    final unmetRequirements = requirements.where((req) => !req.isMet).toList();
    final allMet = unmetRequirements.isEmpty;

    if (!showAll && password.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: allMet && password.isNotEmpty
            ? theme.colorScheme.primaryContainer.withOpacity(0.3)
            : theme.colorScheme.errorContainer.withOpacity(0.3),
        border: Border.all(
          color: allMet && password.isNotEmpty
              ? theme.colorScheme.primary
              : theme.colorScheme.error,
          width: 1,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                allMet && password.isNotEmpty
                    ? Icons.check_circle
                    : Icons.info_outline,
                size: 16,
                color: allMet && password.isNotEmpty
                    ? theme.colorScheme.primary
                    : theme.colorScheme.error,
              ),
              const SizedBox(width: 8),
              Text(
                'Password Requirements',
                style: theme.textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: allMet && password.isNotEmpty
                      ? theme.colorScheme.primary
                      : theme.colorScheme.error,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (showAll || password.isNotEmpty)
            ...requirements.map((req) => _buildRequirementRow(req, theme)),
          if (!showAll && unmetRequirements.isNotEmpty)
            ...unmetRequirements.map((req) => _buildRequirementRow(req, theme)),
        ],
      ),
    );
  }

  Widget _buildRequirementRow(_PasswordRequirement req, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            req.isMet ? Icons.check : Icons.close,
            size: 16,
            color: req.isMet
                ? theme.colorScheme.primary
                : theme.colorScheme.error,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              req.text,
              style: theme.textTheme.bodySmall?.copyWith(
                color: req.isMet
                    ? theme.colorScheme.onSurface
                    : theme.colorScheme.error,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Validation methods
  bool _hasUppercase(String password) {
    return RegExp(r'[A-Z]').hasMatch(password);
  }

  bool _hasLowercase(String password) {
    return RegExp(r'[a-z]').hasMatch(password);
  }

  bool _hasDigit(String password) {
    return RegExp(r'\d').hasMatch(password);
  }

  bool _hasSpecialChar(String password) {
    return RegExp(r'[!@#\$%^&*(),.?":{}|<>]').hasMatch(password);
  }

  bool _isWeakPassword(String password) {
    final weakPasswords = [
      'password',
      'password123',
      '12345678',
      'qwerty123',
      'admin123',
      'letmein123',
      'welcome123',
      'password1',
      'password1',
      'admin1234'
    ];
    return weakPasswords.contains(password.toLowerCase());
  }

  bool _hasSequentialChars(String password) {
    if (password.length < 3) return false;
    
    final lower = password.toLowerCase();
    for (int i = 0; i <= lower.length - 3; i++) {
      final char1 = lower.codeUnitAt(i);
      final char2 = lower.codeUnitAt(i + 1);
      final char3 = lower.codeUnitAt(i + 2);
      
      // Check ascending sequence
      if (char2 == char1 + 1 && char3 == char2 + 1) {
        return true;
      }
      
      // Check descending sequence
      if (char2 == char1 - 1 && char3 == char2 - 1) {
        return true;
      }
    }
    return false;
  }

  bool _hasRepeatedChars(String password) {
    if (password.length < 3) return false;
    
    int count = 1;
    for (int i = 1; i < password.length; i++) {
      if (password[i] == password[i - 1]) {
        count++;
        if (count > 2) return true;
      } else {
        count = 1;
      }
    }
    return false;
  }

  static bool isPasswordValid(String password) {
    final widget = PasswordRequirementsWidget(password: password);
    return password.length >= 8 &&
        widget._hasUppercase(password) &&
        widget._hasLowercase(password) &&
        widget._hasDigit(password) &&
        widget._hasSpecialChar(password) &&
        !widget._isWeakPassword(password) &&
        !widget._hasSequentialChars(password) &&
        !widget._hasRepeatedChars(password);
  }
}

class _PasswordRequirement {
  final String text;
  final bool isMet;

  _PasswordRequirement({
    required this.text,
    required this.isMet,
  });
}