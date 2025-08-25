// lib/features/admin/docs_page.dart
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

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
  bool _deleting = false;
  String? _error;

  // UX helpers
  String _q = '';
  String _sortKey = 'date'; // 'date' | 'name'
  bool _sortAsc = false;

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
          'This will delete the document, its chunks, and its vectors.',
        ),
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

    setState(() => _deleting = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final resp = await dio.delete('/admin/docs/$id');

      if (resp.statusCode != null && resp.statusCode! >= 400) {
        throw DioException(
          requestOptions: resp.requestOptions,
          response: resp,
          message: resp.data?.toString(),
        );
      }

      if (!mounted) return;
      setState(() => _docs.removeWhere((e) => e['id'] == id));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Document deleted')),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Delete failed: ${e.response?.data ?? e.message}')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Delete failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  List<Map<String, dynamic>> get _filteredSorted {
    // filter
    final q = _q.trim().toLowerCase();
    var list = _docs.where((d) {
      if (q.isEmpty) return true;
      final name = (d['name'] ?? d['filename'] ?? '').toString().toLowerCase();
      return name.contains(q);
    }).toList();

    // sort
    int cmpStr(String a, String b) => a.toLowerCase().compareTo(b.toLowerCase());
    int cmpDate(String? a, String? b) {
      if (a == null && b == null) return 0;
      if (a == null) return -1;
      if (b == null) return 1;
      DateTime? pa, pb;
      try { pa = DateTime.tryParse(a); } catch (_) {}
      try { pb = DateTime.tryParse(b); } catch (_) {}
      if (pa == null && pb == null) return 0;
      if (pa == null) return -1;
      if (pb == null) return 1;
      return pa.compareTo(pb);
    }

    list.sort((a, b) {
      if (_sortKey == 'name') {
        final an = (a['name'] ?? a['filename'] ?? '').toString();
        final bn = (b['name'] ?? b['filename'] ?? '').toString();
        return _sortAsc ? cmpStr(an, bn) : cmpStr(bn, an);
      } else {
        // date
        final ad = a['created_at']?.toString();
        final bd = b['created_at']?.toString();
        return _sortAsc ? cmpDate(ad, bd) : cmpDate(bd, ad);
      }
    });

    return list;
  }

  @override
  Widget build(BuildContext context) {
    final toolbar = Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        // Search
        SizedBox(
          width: 260,
          child: TextField(
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search documents…',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (v) => setState(() => _q = v),
          ),
        ),
        // Sort controls
        DropdownButton<String>(
          value: _sortKey,
          items: const [
            DropdownMenuItem(value: 'date', child: Text('Sort by date')),
            DropdownMenuItem(value: 'name', child: Text('Sort by name')),
          ],
          onChanged: (v) => setState(() => _sortKey = v ?? 'date'),
        ),
        IconButton(
          tooltip: _sortAsc ? 'Ascending' : 'Descending',
          onPressed: () => setState(() => _sortAsc = !_sortAsc),
          icon: Icon(_sortAsc ? Icons.arrow_upward : Icons.arrow_downward),
        ),
        const SizedBox(width: 8),
        FilledButton.icon(
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.refresh),
          label: const Text('Refresh'),
        ),
      ],
    );

    final list = _filteredSorted;

    return Stack(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(
              children: [
                Expanded(
                  child: Text('Documents', style: Theme.of(context).textTheme.headlineSmall),
                ),
                // quick nav to upload if you want
                OutlinedButton.icon(
                  onPressed: () => context.go('/a/upload'),
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Upload'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 12),
            toolbar,
            const SizedBox(height: 12),
            Expanded(
              child: list.isEmpty && !_loading
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.description_outlined, size: 48, color: Colors.grey),
                          const SizedBox(height: 8),
                          const Text('No documents found'),
                          const SizedBox(height: 8),
                          OutlinedButton.icon(
                            onPressed: _load,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Reload'),
                          ),
                        ],
                      ),
                    )
                  : ListView.separated(
                      itemCount: list.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, i) {
                        final doc = list[i];
                        final id = doc['id'] as int?;
                        final name = (doc['name'] ?? doc['filename'] ?? 'Untitled').toString();
                        final created = doc['created_at']?.toString();
                        final chunkCount = doc['chunk_count']; // show if backend includes it

                        return Card(
                          child: ListTile(
                            title: Text(name),
                            subtitle: Row(
                              children: [
                                if (created != null) Text('Created: $created'),
                                if (created != null && chunkCount != null) const SizedBox(width: 12),
                                if (chunkCount != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.deepPurple.withValues(alpha: .08),
                                      borderRadius: BorderRadius.circular(999),
                                    ),
                                    child: Text('Chunks: $chunkCount',
                                        style: const TextStyle(fontSize: 12)),
                                  ),
                              ],
                            ),
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
                                  onPressed: (_deleting || id == null)
                                      ? null
                                      : () => _deleteDoc(id),
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
        ),

        // Small blocking overlay when deleting to prevent double taps
        if (_deleting)
          Container(
            color: Colors.black.withValues(alpha: .05),
            child: const Center(
              child: SizedBox(
                width: 36,
                height: 36,
                child: CircularProgressIndicator(strokeWidth: 3),
              ),
            ),
          ),
      ],
    );
  }
}
