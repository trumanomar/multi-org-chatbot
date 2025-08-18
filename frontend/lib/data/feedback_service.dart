import 'package:frontend/data/api_client.dart';
import 'package:frontend/data/models/feedback.dart';

class FeedbackService {
  final ApiClient _client;

  FeedbackService(this._client);

  Future<List<FeedbackModel>> getFeedback() async {
    try {
      final response = await _client.dio.get('/feedback/get');
      if (response.statusCode != 200) {
        throw Exception('Failed to load feedback: ${response.statusMessage}');
      }

      final List<dynamic> data = response.data;
      return data.map((json) => FeedbackModel.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Failed to load feedback: $e');
    }
  }
}
