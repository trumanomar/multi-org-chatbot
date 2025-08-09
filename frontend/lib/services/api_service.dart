import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ApiService {
  final String baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';

  Future<bool> health() async {
    final res = await http.get(Uri.parse('$baseUrl/health'));
    return res.statusCode == 200;
  }
}
