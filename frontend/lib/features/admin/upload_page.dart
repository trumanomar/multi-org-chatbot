import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class UploadPage extends ConsumerStatefulWidget {
  const UploadPage({super.key});
  @override
  ConsumerState<UploadPage> createState() => _UploadPageState();
}

class _UploadPageState extends ConsumerState<UploadPage> {
  bool _loading = false;
  String? _error;
  String? _ok;

  Future<void> _pickAndUpload() async {
    setState(() { _loading = true; _error = null; _ok = null; });
    try {
      final res = await FilePicker.platform.pickFiles(allowMultiple: true, withData: kIsWeb);
      if (res == null || res.files.isEmpty) { setState(() => _loading = false); return; }

      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dioWithLongTimeout;

      final form = FormData();
      for (final f in res.files) {
        if (kIsWeb) {
          final bytes = f.bytes;
          if (bytes == null) continue;
          form.files.add(MapEntry('files', MultipartFile.fromBytes(bytes, filename: f.name)));
        } else {
          form.files.add(MapEntry('files', await MultipartFile.fromFile(f.path!, filename: f.name)));
        }
      }

      final resp = await dio.post('/admin/upload', data: form);
      if (resp.statusCode! >= 200 && resp.statusCode! < 300) {
        setState(() => _ok = 'Uploaded successfully');
      } else {
        throw Exception(resp.data?.toString() ?? 'Upload failed');
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Upload documents', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null) ...[
          const SizedBox(height: 8),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_ok != null) ...[
          const SizedBox(height: 8),
          Text(_ok!, style: const TextStyle(color: Colors.green)),
        ],
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: _loading ? null : _pickAndUpload, icon: const Icon(Icons.upload_file), label: const Text('Pick & upload')),
      ]),
    );
  }
}
