import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class CreateDomainPage extends ConsumerStatefulWidget {
  const CreateDomainPage({super.key});
  @override
  ConsumerState<CreateDomainPage> createState() => _CreateDomainPageState();
}

class _CreateDomainPageState extends ConsumerState<CreateDomainPage> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  String? _status;
  bool _loading = false;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      // If your backend exposes POST /super-admin/domain/create
      final res = await dio.post('/super-admin/domain/create', data: {'name': _name.text.trim()});
      setState(() => _status = res.data['message']?.toString() ?? 'Created');
    } on DioException catch (e) {
      setState(() => _status = 'Error: ${e.response?.data ?? e.message}');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Domain')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _form,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: _name,
                      decoration: const InputDecoration(labelText: 'Domain Name'),
                      validator: (v) => v!.isEmpty ? 'Required' : null,
                    ),
                    const SizedBox(height: 16),
                    if (_status != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(_status!),
                      ),
                    FilledButton(
                      onPressed: _loading ? null : _submit,
                      child: _loading
                          ? const SizedBox(
                              width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Create'),
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
