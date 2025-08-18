import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ApiClient {
  final String? token;
  ApiClient({this.token});

  static const _defaultBase = 'http://127.0.0.1:8000';

  // Trim trailing slashes just in case
  String get baseUrl =>
      (dotenv.env['API_BASE_URL'] ?? _defaultBase).trim().replaceAll(RegExp(r'/+$'), '');

  BaseOptions _options({
    Duration? connect,
    Duration? receive,
    Duration? send,
  }) {
    return BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: connect ?? const Duration(seconds: 10),
      receiveTimeout: receive ?? const Duration(seconds: 20),
      sendTimeout: send ?? const Duration(seconds: 20),
      headers: {
        if (token != null && token!.isNotEmpty) 'Authorization': 'Bearer $token',
        'Accept': 'application/json',
      },
      // We want the response body even on 4xx/5xx for better error messages
      validateStatus: (code) => code != null && code >= 200 && code < 600,
      responseType: ResponseType.json,
    );
  }

  Dio get dio {
    final d = Dio(_options());
    if (kDebugMode) {
      d.interceptors.add(LogInterceptor(requestBody: true, responseBody: false));
    }
    return d;
  }

  /// Use this for long-running calls (e.g., /chat/query with Ollama).
  Dio get dioWithLongTimeout {
    final d = Dio(_options(
      connect: const Duration(seconds: 20),
      receive: const Duration(seconds: 120),
      send: const Duration(seconds: 60),
    ));
    if (kDebugMode) {
      d.interceptors.add(LogInterceptor(requestBody: true, responseBody: false));
    }
    return d;
  }

  static final jsonOpts = Options(
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    responseType: ResponseType.json,
  );
}
