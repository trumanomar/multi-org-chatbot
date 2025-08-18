import 'package:jwt_decoder/jwt_decoder.dart';
import 'role.dart';

class JwtInfo {
  final String token; final UserRole role; final int? domainId;
  JwtInfo(this.token, this.role, this.domainId);
}
JwtInfo parseJwt(String token) {
  final map = JwtDecoder.decode(token);
  final role = parseRole(map['role']?.toString());
  final did = map['domain_id'];
  final parsed = did is int ? did : (did is String ? int.tryParse(did) : null);
  return JwtInfo(token, role, parsed);
}
