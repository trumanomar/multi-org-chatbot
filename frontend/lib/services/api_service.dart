import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  // ---- flip this to false when backend stubs are live ----
  static const bool useStubs = true;

  final _storage = const FlutterSecureStorage();
  final String baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';

  // ---------- HEALTH ----------
  Future<bool> healthCheck() async {
    if (useStubs) {
      await Future.delayed(const Duration(milliseconds: 300));
      return true;
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/health'));
      if (res.statusCode != 200) return false;
      final data = jsonDecode(res.body);
      // accept either {ok:true} or {status:"ok"}
      return data['ok'] == true || data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  // ---------- LOGIN ----------
  Future<bool> loginAdmin(String email, String password) async {
    if (useStubs) {
      // pretend login succeeded and store a fake token/org
      await Future.delayed(const Duration(milliseconds: 500));
      await _storage.write(key: 'token', value: 'fake-jwt');
      await _storage.write(key: 'org_id', value: 'demo-org');
      await _storage.write(key: 'role', value: 'admin');
      return true;
    }

    final uri = Uri.parse('$baseUrl/auth/login');
    final res = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      await _storage.write(key: 'token', value: data['access_token']);
      await _storage.write(key: 'org_id', value: data['org_id'] ?? 'demo-org');
      await _storage.write(key: 'role', value: data['role'] ?? 'admin');
      return true;
    }
    return false;
  }

  // ---------- UPLOAD ----------
  Future<bool> uploadFile({
    required String filename,
    String? filepath,         // desktop/native
    List<int>? fileBytes,     // web
  }) async {
    if (useStubs) {
      await Future.delayed(const Duration(milliseconds: 500));
      return true;
    }

  Future<bool> healthCheck() async {
  final url = Uri.parse('$baseUrl/health');
  final response = await http.get(url);

  if (response.statusCode == 200) {
    return true;
  }
  return false;
}

    final token = await _storage.read(key: 'token');
    final uri = Uri.parse('$baseUrl/admin/upload');

    final req = http.MultipartRequest('POST', uri);
    if (token != null) req.headers['Authorization'] = 'Bearer $token';

    if (kIsWeb) {
      if (fileBytes == null) return false;
      req.files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: filename,
        contentType: MediaType('application', 'octet-stream'),
      ));
    } else {
      if (filepath == null) return false;
      req.files.add(await http.MultipartFile.fromPath(
        'file',
        filepath,
        filename: filename,
      ));
    }

    final res = await req.send();
    return res.statusCode == 200;
  }
}
