import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class AdminDocDetailPage extends ConsumerStatefulWidget {
  final int docId;
  const AdminDocDetailPage({super.key, required this.docId});

  @override
  ConsumerState<AdminDocDetailPage> createState() => _AdminDocDetailPageState();
}

class _AdminDocDetailPageState extends ConsumerState<AdminDocDetailPage> {
  List<dynamic> _chunks = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _chunks = [];
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      Future<Response> try1() =>
          dio.get('/admin/chunks', queryParameters: {'doc_id': widget.docId});
      Future<Response> try2() => dio.get('/admin/docs/${widget.docId}/chunks');
      Future<Response> try3() => dio.get('/admin/doc/${widget.docId}/chunks');
      Future<Response> try4() =>
          dio.get('/admin/chunk', queryParameters: {'doc_id': widget.docId});

      Response res;
      try {
        res = await try1();
      } catch (_) {
        try {
          res = await try2();
        } catch (_) {
          try {
            res = await try3();
          } catch (_) {
            res = await try4();
          }
        }
      }

      final data = res.data;
      final list = data is List
          ? data
          : (data is Map && data['chunks'] is List)
              ? (data['chunks'] as List)
              : <dynamic>[];

      setState(() => _chunks = list);
    } on DioException catch (e) {
      final body = e.response?.data;
      setState(() => _error = (body is String ? body : body?.toString()) ?? e.message ?? 'Error');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Doc #${widget.docId} — Chunks',
            style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        const SizedBox(height: 8),
        Expanded(
          child: _chunks.isEmpty && !_loading
              ? const Center(child: Text('No chunks found'))
              : ListView.separated(
                  itemCount: _chunks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final c = _chunks[i];
                    final text =
                        (c is Map ? (c['content'] ?? c['page_content']) : c)
                            ?.toString() ??
                            '';
                    final meta = (c is Map ? c['meta_data'] ?? c['metadata'] : null);
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SelectableText(text, maxLines: 10),
                            if (meta != null) ...[
                              const SizedBox(height: 8),
                              Text('meta: $meta',
                                  style: Theme.of(context).textTheme.bodySmall),
                            ],
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
