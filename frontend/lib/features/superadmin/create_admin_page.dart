import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class CreateAdminPage extends ConsumerStatefulWidget {
  const CreateAdminPage({super.key});

  @override
  ConsumerState<CreateAdminPage> createState() => _CreateAdminPageState();
}

class _CreateAdminPageState extends ConsumerState<CreateAdminPage> {
  final _form = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _loadingDomains = false;
  String? _domainsError;
  List<Map<String, dynamic>> _domains = [];
  int? _selectedDomainId;

  bool _submitting = false;
  String? _submitError;
  String? _submitOk;
  bool _passwordObscured = true;
  bool _showPasswordRequirements = false;
  String? _serverPasswordError;

  @override
  void initState() {
    super.initState();
    _loadDomains();
    
    // Listen to password changes to show/hide requirements
    _password.addListener(() {
      setState(() {
        _showPasswordRequirements = _password.text.isNotEmpty;
        _submitError = null; // Clear submit error on password change
        _serverPasswordError = null; // Clear server error on password change
      });
    });
  }

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> _coerceDomains(dynamic data) {
    final out = <Map<String, dynamic>>[];

    // 1) raw list
    if (data is List) {
      for (final e in data) {
        if (e is Map) out.add(Map<String, dynamic>.from(e));
      }
      return out;
    }

    // 2) common envelopes
    if (data is Map) {
      for (final key in const ['domains', 'items', 'data', 'results']) {
        final v = data[key];
        if (v is List) {
          for (final e in v) {
            if (e is Map) out.add(Map<String, dynamic>.from(e));
          }
          return out;
        }
      }
    }

    return out;
  }

  Future<void> _loadDomains() async {
    if (!mounted) return;
    setState(() {
      _loadingDomains = true;
      _domainsError = null;
      _submitOk = null;
      _submitError = null;
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.get('/super-admin/domains');

      final list = _coerceDomains(res.data)
          .where((m) => m.containsKey('id') && m.containsKey('name'))
          .toList();

      // Reset selection if it's not in the new list
      int? nextSelected;
      if (_selectedDomainId != null &&
          list.any((d) => d['id'] == _selectedDomainId)) {
        nextSelected = _selectedDomainId;
      } else {
        nextSelected = null; // force user to choose one
      }

      if (!mounted) return;
      setState(() {
        _domains = list;
        _selectedDomainId = nextSelected;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _domainsError = e.response?.data?.toString() ?? e.message ?? 'Error loading domains';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _domainsError = e.toString();
      });
    } finally {
      if (!mounted) return;
      setState(() => _loadingDomains = false);
    }
  }

  // Password validation methods
  bool _hasUppercase(String password) => RegExp(r'[A-Z]').hasMatch(password);
  bool _hasLowercase(String password) => RegExp(r'[a-z]').hasMatch(password);
  bool _hasDigit(String password) => RegExp(r'\d').hasMatch(password);
  bool _hasSpecialChar(String password) => RegExp(r'[!@#\$%^&*(),.?":{}|<>]').hasMatch(password);
  
  bool _isWeakPassword(String password) {
    final weakPasswords = [
      'password', 'password123', '12345678', 'qwerty123',
      'admin123', 'letmein123', 'welcome123', 'password1',
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
      
      // Check ascending or descending sequence
      if ((char2 == char1 + 1 && char3 == char2 + 1) ||
          (char2 == char1 - 1 && char3 == char2 - 1)) {
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

  bool _isPasswordValid(String password) {
    return password.length >= 8 &&
        _hasUppercase(password) &&
        _hasLowercase(password) &&
        _hasDigit(password) &&
        _hasSpecialChar(password) &&
        !_isWeakPassword(password) &&
        !_hasSequentialChars(password) &&
        !_hasRepeatedChars(password);
  }

  Widget _buildPasswordRequirements() {
    final theme = Theme.of(context);
    final password = _password.text;
    
    final requirements = [
      {'text': 'At least 8 characters long', 'met': password.length >= 8},
      {'text': 'Contains uppercase letter (A-Z)', 'met': _hasUppercase(password)},
      {'text': 'Contains lowercase letter (a-z)', 'met': _hasLowercase(password)},
      {'text': 'Contains at least one digit (0-9)', 'met': _hasDigit(password)},
      {'text': 'Contains special character (!@#\$%^&*(),.?":{}|<>)', 'met': _hasSpecialChar(password)},
      {'text': 'No common weak passwords', 'met': !_isWeakPassword(password)},
      {'text': 'No sequential characters (e.g., 123, abc)', 'met': !_hasSequentialChars(password)},
      {'text': 'No more than 2 consecutive identical characters', 'met': !_hasRepeatedChars(password)},
    ];

    final allMet = requirements.every((req) => req['met'] as bool);

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
          ...requirements.map((req) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  req['met'] as bool ? Icons.check : Icons.close,
                  size: 16,
                  color: req['met'] as bool
                      ? theme.colorScheme.primary
                      : theme.colorScheme.error,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    req['text'] as String,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: req['met'] as bool
                          ? theme.colorScheme.onSurface
                          : theme.colorScheme.error,
                    ),
                  ),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }

  String _extractPasswordErrors(dynamic error) {
    if (error is Map && error.containsKey('detail')) {
      final detail = error['detail'];
      if (detail is Map && detail.containsKey('errors')) {
        final errors = detail['errors'];
        if (errors is List) {
          return errors.join('\n');
        }
      }
      if (detail is String) {
        return detail;
      }
    }
    return error.toString();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    if (_selectedDomainId == null) {
      setState(() => _submitError = 'Please select a domain');
      return;
    }

    // Client-side password validation
    if (!_isPasswordValid(_password.text)) {
      setState(() {
        _showPasswordRequirements = true;
        _submitError = 'Password does not meet all requirements. Please check below.';
      });
      return;
    }

    if (!mounted) return;
    setState(() {
      _submitting = true;
      _submitError = null;
      _submitOk = null;
      _serverPasswordError = null;
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      final body = {
        'username': _username.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
        'domain_id': _selectedDomainId,
      };

      await dio.post('/super-admin/admin/create', data: body);

      if (!mounted) return;
      setState(() {
        _submitOk = 'Admin created successfully';
        _username.clear();
        _email.clear();
        _password.clear();
        _showPasswordRequirements = false;
        // keep selected domain as-is
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Admin created successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } on DioException catch (e) {
      String errorMessage = 'Create failed';
      
      if (e.response?.data != null) {
        final responseData = e.response!.data;
        
        // Check if it's a password validation error
        if (responseData is Map && 
            responseData.toString().toLowerCase().contains('password validation failed')) {
          setState(() {
            _serverPasswordError = _extractPasswordErrors(responseData);
            _showPasswordRequirements = true;
          });
          errorMessage = 'Password validation failed. Please check the requirements below.';
        } else {
          errorMessage = _extractPasswordErrors(responseData);
        }
      }

      if (!mounted) return;
      setState(() {
        _submitError = errorMessage;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitError = e.toString();
      });
    } finally {
      if (!mounted) return;
      setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final headline = theme.textTheme.headlineSmall;

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: SingleChildScrollView(
                child: Form(
                  key: _form,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Text('Create Admin', style: headline),
                          const Spacer(),
                          IconButton(
                            tooltip: 'Refresh domains',
                            onPressed: _loadingDomains ? null : _loadDomains,
                            icon: const Icon(Icons.refresh),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // Domains row – shows loading / error / dropdown
                      if (_loadingDomains) const LinearProgressIndicator(),
                      if (_domainsError != null) ...[
                        const SizedBox(height: 8),
                        Text(_domainsError!, style: const TextStyle(color: Colors.red)),
                      ],
                      const SizedBox(height: 8),
                      DropdownButtonFormField<int>(
                        decoration: const InputDecoration(
                          labelText: 'Domain',
                          border: OutlineInputBorder(),
                        ),
                        isExpanded: true,
                        value: (_selectedDomainId != null &&
                                _domains.any((d) => d['id'] == _selectedDomainId))
                            ? _selectedDomainId
                            : null,
                        items: _domains
                            .map((d) => DropdownMenuItem<int>(
                                  value: d['id'] as int,
                                  child: Text(d['name']?.toString() ?? 'Unnamed'),
                                ))
                            .toList(),
                        onChanged: _loadingDomains
                            ? null
                            : (v) => setState(() => _selectedDomainId = v),
                        validator: (v) => v == null ? 'Select a domain' : null,
                      ),

                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _username,
                        textInputAction: TextInputAction.next,
                        decoration: const InputDecoration(
                          labelText: 'Username',
                          border: OutlineInputBorder(),
                        ),
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return 'Username is required';
                          if (v.trim().length < 3) return 'At least 3 characters';
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _email,
                        textInputAction: TextInputAction.next,
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          border: OutlineInputBorder(),
                        ),
                        validator: (v) {
                          final value = (v ?? '').trim();
                          if (value.isEmpty) return 'Email is required';
                          final emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
                          if (!emailRegex.hasMatch(value)) return 'Enter a valid email';
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      
                      // Password field with visibility toggle
                      TextFormField(
                        controller: _password,
                        obscureText: _passwordObscured,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          border: const OutlineInputBorder(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _passwordObscured ? Icons.visibility : Icons.visibility_off,
                            ),
                            onPressed: () {
                              setState(() {
                                _passwordObscured = !_passwordObscured;
                              });
                            },
                          ),
                        ),
                        validator: (v) {
                          final value = v ?? '';
                          if (value.isEmpty) return 'Password is required';
                          if (!_isPasswordValid(value)) {
                            return 'Password does not meet requirements';
                          }
                          return null;
                        },
                      ),

                      // Server password error
                      if (_serverPasswordError != null) ...[
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.errorContainer.withOpacity(0.3),
                            border: Border.all(color: theme.colorScheme.error),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.error_outline, 
                                  color: theme.colorScheme.error, size: 20),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _serverPasswordError!,
                                  style: TextStyle(color: theme.colorScheme.error),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      // Password requirements widget
                      if (_showPasswordRequirements) ...[
                        const SizedBox(height: 12),
                        _buildPasswordRequirements(),
                      ],

                      const SizedBox(height: 16),
                      
                      // Show password requirements button
                      if (!_showPasswordRequirements && _password.text.isEmpty)
                        OutlinedButton.icon(
                          onPressed: () {
                            setState(() {
                              _showPasswordRequirements = true;
                            });
                          },
                          icon: const Icon(Icons.info_outline),
                          label: const Text('Show Password Requirements'),
                        ),
                      
                      const SizedBox(height: 12),

                      if (_submitError != null) ...[
                        Text(_submitError!, style: const TextStyle(color: Colors.red)),
                        const SizedBox(height: 8),
                      ],
                      if (_submitOk != null) ...[
                        Text(_submitOk!, style: const TextStyle(color: Colors.green)),
                        const SizedBox(height: 8),
                      ],
                      SizedBox(
                        height: 44,
                        child: FilledButton.icon(
                          onPressed: _submitting ? null : _submit,
                          icon: _submitting
                              ? const SizedBox(
                                  width: 18, height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.admin_panel_settings),
                          label: const Text('Create Admin'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}