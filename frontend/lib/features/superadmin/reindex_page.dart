import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class ReindexPage extends ConsumerStatefulWidget {
  const ReindexPage({super.key});

  @override
  ConsumerState<ReindexPage> createState() => _ReindexPageState();
}

class _ReindexPageState extends ConsumerState<ReindexPage> {
  bool _running = false;
  String? _result;
  String? _error;

  Future<void> _runReindex() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reindex embeddings?'),
        content: const Text(
          'This will rebuild the vector index (can take a while). '
          'Proceed?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Run')),
        ],
      ),
    );
    if (ok != true) return;

    setState(() {
      _running = true;
      _result = null;
      _error = null;
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      // Backend usually exposes POST /super-admin/reindex (adjust if yours differs)
      final resp = await dio.post('/super-admin/reindex', options: ApiClient.jsonOpts);

      if (resp.statusCode != null && resp.statusCode! >= 400) {
        throw DioException(
          requestOptions: resp.requestOptions,
          response: resp,
          message: resp.data?.toString(),
        );
      }

      setState(() => _result = resp.data?.toString() ?? 'Reindex started/completed.');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Reindex request sent')),
        );
      }
    } on DioException catch (e) {
      setState(() => _error = e.response?.data?.toString() ?? e.message ?? 'Request failed');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Reindex Embeddings', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          const Text(
            'Use this tool to rebuild the vector index (e.g., after changing embedding model '
            'or importing a lot of documents).',
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _running ? null : _runReindex,
            icon: const Icon(Icons.refresh),
            label: _running ? const Text('Running…') : const Text('Run reindex'),
          ),
          const SizedBox(height: 16),
          if (_running) const LinearProgressIndicator(),
          if (_result != null) ...[
            const SizedBox(height: 12),
            const Text('Result:', style: TextStyle(fontWeight: FontWeight.bold)),
            SelectableText(_result!),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
        ],
      ),
    );
  }
}
