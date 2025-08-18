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

  @override
  void initState() {
    super.initState();
    _loadDomains();
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

      // Reset selection if it’s not in the new list
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

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    if (_selectedDomainId == null) {
      setState(() => _submitError = 'Please select a domain');
      return;
    }

    if (!mounted) return;
    setState(() {
      _submitting = true;
      _submitError = null;
      _submitOk = null;
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
        // keep selected domain as-is
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Admin created')),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _submitError = e.response?.data?.toString() ?? e.message ?? 'Create failed';
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
    final headline = Theme.of(context).textTheme.headlineSmall;

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(24),
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
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Enter username' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _email,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Email',
                        border: OutlineInputBorder(),
                      ),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Enter email' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Password',
                        border: OutlineInputBorder(),
                      ),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Enter password' : null,
                    ),

                    const SizedBox(height: 16),
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
                      child: FilledButton(
                        onPressed: _submitting ? null : _submit,
                        child: _submitting
                            ? const SizedBox(
                                width: 18, height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Create admin'),
                      ),
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
