import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class AdminDocsPage extends ConsumerStatefulWidget {
  const AdminDocsPage({super.key});
  @override
  ConsumerState<AdminDocsPage> createState() => _AdminDocsPageState();
}

class _AdminDocsPageState extends ConsumerState<AdminDocsPage> {
  List<Map<String, dynamic>> _docs = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  List<Map<String, dynamic>> _coerceDocs(dynamic data) {
    final out = <Map<String, dynamic>>[];

    // 1) Bare list
    if (data is List) {
      for (final e in data) {
        if (e is Map) out.add(Map<String, dynamic>.from(e));
      }
      return out;
    }

    // 2) Wrapped in a map: docs/items/data/results
    if (data is Map) {
      for (final key in const ['docs', 'items', 'data', 'results']) {
        final v = data[key];
        if (v is List) {
          for (final e in v) {
            if (e is Map) out.add(Map<String, dynamic>.from(e));
          }
          return out;
        }
      }
    }

    return out; // unknown shape → empty
  }

  Future<void> _load() async {
    if (mounted) setState(() => _loading = true);
    _error = null;
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.get('/admin/docs');

      final list = _coerceDocs(res.data);

      if (!mounted) return;
      setState(() => _docs = list);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.response?.data?.toString() ?? e.message ?? 'Error');
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _deleteDoc(int id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Delete document?'),
        content: const Text(
            'This will delete the document, its chunks, and its vectors.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      await dio.delete('/admin/docs/$id');

      if (!mounted) return;
      setState(() => _docs.removeWhere((e) => e['id'] == id));
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Document deleted')));
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Delete failed: ${e.response?.data ?? e.message}')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Delete failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Documents', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null) ...[
          const SizedBox(height: 8),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        const SizedBox(height: 8),
        Expanded(
          child: _docs.isEmpty && !_loading
              ? const Center(child: Text('No documents found'))
              : ListView.separated(
                  itemCount: _docs.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final doc = _docs[i];
                    final id = doc['id'] as int?;
                    final name = (doc['name'] ?? doc['filename'] ?? 'Untitled').toString();
                    final created = doc['created_at']?.toString();

                    return Card(
                      child: ListTile(
                        title: Text(name),
                        subtitle: created == null ? null : Text('Created: $created'),
                        trailing: Wrap(
                          spacing: 8,
                          children: [
                            OutlinedButton.icon(
                              onPressed: id == null ? null : () => context.go('/a/docs/$id'),
                              icon: const Icon(Icons.list_alt),
                              label: const Text('View chunks'),
                            ),
                            FilledButton.icon(
                              style: FilledButton.styleFrom(
                                backgroundColor: Colors.red.shade600,
                              ),
                              onPressed: id == null ? null : () => _deleteDoc(id),
                              icon: const Icon(Icons.delete_forever),
                              label: const Text('Delete'),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}
