import 'api_client.dart';
import '../core/jwt.dart';

class LoginResult {
  final JwtInfo jwt; final String redirect;
  LoginResult(this.jwt, this.redirect);
}

class AuthRepository {
  final ApiClient _client = ApiClient();
  Future<LoginResult> login(String username, String password) async {
    final res = await _client.dio.post('/auth/login', data: {'username': username, 'password': password});
    final token = res.data['access_token'] as String;
    final redirect = (res.data['redirect'] as String?) ?? '';
    return LoginResult(parseJwt(token), redirect);
  }
}
