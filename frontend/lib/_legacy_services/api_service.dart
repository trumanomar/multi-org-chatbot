import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  final _storage = const FlutterSecureStorage();
  final String baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';

  // -------- Health ----------
  Future<bool> healthCheck() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/health'));
      if (res.statusCode != 200) return false;
      final data = jsonDecode(res.body);
      return data['ok'] == true || data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  // ORG_ID helper (currently unused by /admin/upload, kept for future)
  Future<String?> getOrgId() async {
    return dotenv.env['ORG_ID'] ?? 'demo-org';
  }

  // -------- Upload (matches: files: list[UploadFile]) ----------
  Future<Map<String, dynamic>?> uploadFile({
    required String filename,
    String? filepath,        // desktop/native
    List<int>? fileBytes,    // web
  }) async {
    final uri = Uri.parse('$baseUrl/admin/upload');
    final req = http.MultipartRequest('POST', uri);

    // IMPORTANT: backend expects the field name 'files' (plural), even for one file
    if (kIsWeb) {
      if (fileBytes == null) {
        return {"status": "error", "body": "No file bytes"};
      }
      req.files.add(http.MultipartFile.fromBytes(
        'files', // <-- must be 'files'
        fileBytes,
        filename: filename,
        contentType: MediaType('application', 'octet-stream'),
      ));
    } else {
      if (filepath == null) {
        return {"status": "error", "body": "No file path"};
      }
      req.files.add(await http.MultipartFile.fromPath(
        'files', // <-- must be 'files'
        filepath,
        filename: filename,
      ));
    }

    final streamed = await req.send();
    final resp = await http.Response.fromStream(streamed);

    // Helpful while wiring things up:
    // ignore: avoid_print
    print('UPLOAD status=${resp.statusCode} body=${resp.body}');

    if (resp.statusCode == 200) {
      // Backend returns: {"message": "Indexed X chunks from Y file(s)"}
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    return {"status": "error", "code": resp.statusCode, "body": resp.body};
  }

  // -------- Chat ----------
  Future<Map<String, dynamic>?> chatQuery(String message) async {
    final res = await http.post(
      Uri.parse('$baseUrl/chat/query'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'message': message}),
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    return null;
  }
}
