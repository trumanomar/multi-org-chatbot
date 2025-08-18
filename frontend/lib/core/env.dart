import 'package:flutter_dotenv/flutter_dotenv.dart';
class Env {
  static String get apiBase =>
      dotenv.env['API_BASE'] ??
      dotenv.env['API_BASE_URL'] ??
      'http://127.0.0.1:8000';
}
