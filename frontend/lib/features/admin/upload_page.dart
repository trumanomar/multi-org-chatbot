import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class UploadPage extends ConsumerStatefulWidget {
  const UploadPage({super.key});
  @override ConsumerState<UploadPage> createState() => _UploadPageState();
}
class _UploadPageState extends ConsumerState<UploadPage> {
  String? status;
  Future<void> pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(allowMultiple: true);
    if (result == null) return;
    final jwt = ref.read(authControllerProvider).jwt!;
    final dio = ApiClient(token: jwt.token).dio;
    final form = FormData();
    for (final f in result.files) {
      if (f.bytes != null) {
        form.files.add(MapEntry('files', MultipartFile.fromBytes(f.bytes!, filename: f.name)));
      } else if (f.path != null) {
        form.files.add(MapEntry('files', await MultipartFile.fromFile(f.path!, filename: f.name)));
      }
    }
    try {
      final res = await dio.post('/admin/upload', data: form);
      setState(()=> status = res.data['message']);
    } on DioException catch (e) {
      setState(()=> status = 'Upload failed: ${e.message}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(appBar: AppBar(title: const Text('Upload Documents')),
      body: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        FilledButton(onPressed: pickAndUpload, child: const Text('Select files')),
        if (status!=null) Padding(padding: const EdgeInsets.all(12), child: Text(status!)),
      ])));
  }
}
