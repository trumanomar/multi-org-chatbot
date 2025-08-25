import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class DomainsPage extends ConsumerStatefulWidget {
  const DomainsPage({super.key});
  @override
  ConsumerState<DomainsPage> createState() => _DomainsPageState();
}

class _DomainsPageState extends ConsumerState<DomainsPage> {
  bool _loading = false;
  String? _error;
  List<Map<String, dynamic>> _domains = [];

  Future<Dio> _dio() async {
    final jwt = ref.read(authControllerProvider).jwt!;
    return ApiClient(token: jwt.token).dio;
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) setState(() { _loading = true; _error = null; });
    try {
      final dio = await _dio();
      final r = await dio.get('/super-admin/domains');
      final list = (r.data['domains'] as List?) ?? [];
      _domains = list.cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } on DioException catch (e) {
      _error = e.response?.data?.toString() ?? e.message ?? 'Error';
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _delete(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Delete domain?'),
        content: const Text(
          'This permanently removes the domain and deactivates its users/admins.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogCtx).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(dialogCtx).pop(true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;

    try {
      final dio = await _dio();
      await dio.delete('/super-admin/domain/$id');
      _domains.removeWhere((e) => e['id'] == id);
      if (mounted) setState(() {});
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Domain deleted')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Delete failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Domains'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 12),
          Expanded(
            child: _domains.isEmpty
                ? const Center(child: Text('No domains'))
                : ListView.separated(
                    itemCount: _domains.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final d = _domains[i];
                      return Card(
                        child: ListTile(
                          title: Text('${d['name']}'),
                          subtitle: Text('ID: ${d['id']} • Created: ${d['created_at']}'),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete, color: Colors.red),
                            onPressed: () => _delete(d['id'] as int),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ]),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.of(context).pushNamed('/s/domain-create'),
        icon: const Icon(Icons.add_business),
        label: const Text('Create Domain'),
      ),
    );
  }
}
