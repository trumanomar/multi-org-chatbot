// lib/features/admin/create_user_page.dart
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import '../../providers/auth_provider.dart';

class CreateUserPage extends ConsumerStatefulWidget {
  const CreateUserPage({super.key});

  @override
  ConsumerState<CreateUserPage> createState() => _CreateUserPageState();
}

class _CreateUserPageState extends ConsumerState<CreateUserPage> {
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _usernameCtrl = TextEditingController();
  final TextEditingController _emailCtrl = TextEditingController();
  final TextEditingController _passwordCtrl = TextEditingController();

  bool _submitting = false;
  bool _loadingDomains = false;
  List<Map<String, dynamic>> _domains = [];
  int? _selectedDomainId;
  String? _currentDomainName;

  @override
  void initState() {
    super.initState();
    _loadDomains();
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<Dio> _dio() async {
    final base = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
    final token = ref.read(authControllerProvider).jwt?.token;

    final d = Dio(
      BaseOptions(
        baseUrl: base,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(minutes: 2),
        sendTimeout: const Duration(minutes: 2),
        headers: {
          'Accept': 'application/json',
          if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
        },
      ),
    );

    d.interceptors.add(LogInterceptor(requestBody: true, responseBody: true));
    return d;
  }

  Future<void> _loadDomains() async {
    setState(() {
      _loadingDomains = true;
    });

    try {
      final dio = await _dio();
      
      // Get domains from admin endpoint
      try {
        final response = await dio.get('/admin/domains');
        final domainsData = response.data['domains'] as List<dynamic>;
        final domains = domainsData.map((d) => Map<String, dynamic>.from(d)).toList();
        
        setState(() {
          _domains = domains;
          // Select the first domain by default
          if (domains.isNotEmpty) {
            _selectedDomainId = domains.first['id'] as int;
            _currentDomainName = domains.first['name'] as String;
          }
        });
      } catch (e) {
        print('Error loading domains: $e');
        // Fallback: create a default domain entry
        setState(() {
          _domains = [{'id': 1, 'name': 'Default Domain'}];
          _selectedDomainId = 1;
          _currentDomainName = 'Default Domain';
        });
      }
    } catch (e) {
      print('Error loading domains: $e');
      // Fallback: create a default domain entry
      setState(() {
        _domains = [{'id': 1, 'name': 'Default Domain'}];
        _selectedDomainId = 1;
        _currentDomainName = 'Default Domain';
      });
    } finally {
      setState(() {
        _loadingDomains = false;
      });
    }
  }

  Future<void> _submit() async {
    if (_submitting) return;
    final form = _formKey.currentState;
    if (form == null) return;
    if (!form.validate()) return;
    
    if (_selectedDomainId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a domain')),
      );
      return;
    }

    setState(() {
      _submitting = true;
    });

    try {
      final dio = await _dio();
      final payload = {
        'username': _usernameCtrl.text.trim(),
        'email': _emailCtrl.text.trim(),
        'password': _passwordCtrl.text,
        'domain_id': _selectedDomainId,
      };

      await dio.post(
        '/admin/create_user',
        data: jsonEncode(payload),
        options: Options(headers: {'Content-Type': 'application/json'}),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User created successfully')),
        );
        Navigator.of(context).maybePop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to create user: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(
              Icons.person_add,
              size: 24,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(width: 8),
            const Text('Create User'),
          ],
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Add a new user to your organization', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      'Admin role: Can only create users in your own domain\nSuper Admin role: Can create users in any domain',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _usernameCtrl,
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
                      controller: _emailCtrl,
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

                    TextFormField(
                      controller: _passwordCtrl,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Password',
                        border: OutlineInputBorder(),
                      ),
                      validator: (v) {
                        final value = v ?? '';
                        if (value.isEmpty) return 'Password is required';
                        if (value.length < 6) return 'At least 6 characters';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    // Domain Selection
                    if (_loadingDomains)
                      const Center(child: CircularProgressIndicator())
                    else if (_domains.isNotEmpty)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<int>(
                                  value: _selectedDomainId,
                                  decoration: const InputDecoration(
                                    labelText: 'Domain',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: _domains.map((domain) {
                                    return DropdownMenuItem<int>(
                                      value: domain['id'] as int,
                                      child: Text(domain['name'] as String),
                                    );
                                  }).toList(),
                                  onChanged: (value) {
                                    setState(() {
                                      _selectedDomainId = value;
                                      if (value != null) {
                                        final domain = _domains.firstWhere((d) => d['id'] == value);
                                        _currentDomainName = domain['name'] as String;
                                      }
                                    });
                                  },
                                  validator: (value) {
                                    if (value == null) return 'Please select a domain';
                                    return null;
                                  },
                                ),
                              ),
                              const SizedBox(width: 8),
                              IconButton(
                                onPressed: _loadDomains,
                                icon: const Icon(Icons.refresh),
                                tooltip: 'Refresh domains',
                              ),
                            ],
                          ),
                          if (_currentDomainName != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'Selected: $_currentDomainName',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.primary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                        ],
                      )
                    else
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('No domains available', style: TextStyle(color: Colors.red)),
                          const SizedBox(height: 8),
                          TextButton.icon(
                            onPressed: _loadDomains,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Retry'),
                          ),
                        ],
                      ),

                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: _submitting ? null : _submit,
                      icon: _submitting
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.person_add),
                      label: const Text('Create User'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}


