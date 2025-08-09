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
  String? _path;           // desktop/native
  Uint8List? _bytes;       // web
  bool _uploading = false;

  Future<void> _pick() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'txt', 'docx', 'csv'],
      withData: kIsWeb, // get bytes on web
    );
    if (result == null) return;
    final file = result.files.single;
    setState(() {
      _filename = file.name;
      _path = file.path;   // null on web
      _bytes = file.bytes; // non-null on web
    });
  }

  Future<void> _upload() async {
    if (_filename == null) return;
    setState(() => _uploading = true);

    final ok = await _api.uploadFile(
      filename: _filename!,
      filepath: _path,
      fileBytes: _bytes,
    );

    setState(() => _uploading = false);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? 'Uploaded!' : 'Upload failed')),
    );
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
            child: _uploading ? const CircularProgressIndicator() : const Text('Upload'),
          ),
        ]),
      ),
    );
  }
}
