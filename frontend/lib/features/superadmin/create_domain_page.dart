import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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
  bool _loading = false;
  String? _error;
  String? _ok;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; _ok = null; });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      Response resp;
      try {
        resp = await dio.post('/super-admin/domain/create',
            data: {'name': _name.text.trim()},
            options: ApiClient.jsonOpts);
      } on DioException catch (e) {
        if (e.response?.statusCode == 404) {
          // try alt endpoint
          resp = await dio.post('/super-admin/domains',
              data: {'name': _name.text.trim()},
              options: ApiClient.jsonOpts);
        } else {
          rethrow;
        }
      }

      if (!mounted) return;
      setState(() => _ok = 'Created: ${resp.data}');
    } on DioException catch (e) {
      setState(() => _error = e.response?.data?.toString() ?? e.message ?? 'Failed');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Create Domain', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          if (_error != null)
            Container(
              width: double.infinity,
              color: Colors.red.shade50,
              padding: const EdgeInsets.all(12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          if (_ok != null)
            Container(
              width: double.infinity,
              color: Colors.green.shade50,
              padding: const EdgeInsets.all(12),
              child: Text(_ok!, style: const TextStyle(color: Colors.green)),
            ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _form,
                child: Column(
                  children: [
                    TextFormField(
                      controller: _name,
                      decoration: const InputDecoration(labelText: 'Organization name'),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter name' : null,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _loading ? null : _submit,
                      child: _loading
                          ? const SizedBox(
                              width: 16, height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Create'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
