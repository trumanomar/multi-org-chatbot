import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});
  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final _api = ApiService();
  String? _filename;
  String? _path;     // desktop/native
  Uint8List? _bytes; // web
  bool _uploading = false;

  Future<void> _pick() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'txt', 'docx', 'csv'],
      withData: kIsWeb, // get bytes on web
    );
    if (result == null) return;
    final f = result.files.single;
    setState(() {
      _filename = f.name;
      _path = f.path;      // null on web
      _bytes = f.bytes;    // non-null on web
    });
  }

  Future<void> _upload() async {
    if (_filename == null) return;
    setState(() => _uploading = true);

    final res = await _api.uploadFile(
      filename: _filename!,
      filepath: _path,      // used on desktop/native
      fileBytes: _bytes,    // used on web
    );

    setState(() => _uploading = false);
    if (!mounted) return;

    final ok = res != null && res['status'] != 'error';
    final msg = ok
        ? (res['message'] ?? 'Uploaded')
        : 'Upload failed (${res?['code'] ?? ''}) ${res?['body'] ?? ''}';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Document')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          Row(children: [
            Expanded(child: Text(_filename ?? 'No file selected')),
            const SizedBox(width: 12),
            ElevatedButton(onPressed: _pick, child: const Text('Choose file')),
          ]),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: (_filename == null || _uploading) ? null : _upload,
            child: _uploading
                ? const SizedBox(
                    width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Upload'),
          ),
        ]),
      ),
    );
  }
}
