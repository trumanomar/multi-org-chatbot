import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class AdminDocChunksPage extends ConsumerStatefulWidget {
  final int? docId;
  const AdminDocChunksPage({super.key, required this.docId});

  @override
  ConsumerState<AdminDocChunksPage> createState() =>
      _AdminDocChunksPageState();
}

class _AdminDocChunksPageState extends ConsumerState<AdminDocChunksPage> {
  bool _loading = false;
  String? _error;
  List<Map<String, dynamic>> _chunks = [];

  @override
  void initState() {
    super.initState();
    if (widget.docId != null) _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.get('/admin/chunks', queryParameters: {'doc_id': widget.docId});
      _chunks = ((res.data['chunks'] as List?) ?? [])
          .map<Map<String, dynamic>>((e) => Map<String, dynamic>.from(e))
          .toList();
      setState(() {});
    } on DioException catch (e) {
      setState(() => _error = e.response?.data?.toString() ?? e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.docId == null) {
      return const Scaffold(
        body: Center(child: Text('Invalid document id')),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text('Chunks for doc #${widget.docId}')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 8),
          Expanded(
            child: _chunks.isEmpty
                ? const Center(child: Text('No chunks found'))
                : ListView.separated(
                    itemCount: _chunks.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final c = _chunks[i];
                      return Card(
                        child: ListTile(
                          title: Text('Chunk #${c['id']}'),
                          subtitle: Text(
                            (c['content'] ?? '').toString(),
                            maxLines: 4,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}
