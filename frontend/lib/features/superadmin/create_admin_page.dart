import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
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
  String? _status;
  bool _loading = false;

  List<Map<String, dynamic>> _domains = [];
  int? _domainId;

  Future<void> _loadDomains() async {
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      // Try common endpoints for domains
      final tries = <Future<Response>>[
        dio.get('/super-admin/domains'),
        dio.get('/domains'),
      ];
      Response res = await tries.first.then((r) => r).catchError((_) async => await tries[1]);
      final list = (res.data as List).cast<dynamic>();
      setState(() {
        _domains = list.map((e) => e as Map<String, dynamic>).toList();
        if (_domains.isNotEmpty) _domainId = _domains.first['id'] as int?;
      });
    } catch (_) {
      // Fall back: leave dropdown empty; user can still create admin if backend ignores domain
    }
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final body = {
        'username': _username.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
        if (_domainId != null) 'domain_id': _domainId,
      };
      final res = await dio.post('/super-admin/admin/create', data: body);
      setState(() => _status = res.data['message']?.toString() ?? 'Created');
    } on DioException catch (e) {
      setState(() => _status = 'Error: ${e.response?.data ?? e.message}');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _loadDomains();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Form(
              key: _form,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                TextFormField(
                  controller: _username,
                  decoration: const InputDecoration(labelText: 'Username'),
                  validator: (v) => v!.isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _email,
                  decoration: const InputDecoration(labelText: 'Email'),
                  validator: (v) => v!.isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  decoration: const InputDecoration(labelText: 'Password'),
                  obscureText: true,
                  validator: (v) => v!.isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  value: _domainId,
                  items: _domains
                      .map((d) => DropdownMenuItem<int>(
                            value: d['id'] as int?,
                            child: Text(d['name']?.toString() ?? 'Domain'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _domainId = v),
                  decoration: const InputDecoration(labelText: 'Domain'),
                ),
                const SizedBox(height: 16),
                if (_status != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(_status!)),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Create'),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
