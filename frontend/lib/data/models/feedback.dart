class FeedbackModel {
  final int id;
  final String content;
  final int rating;
  final DateTime createdAt;   // <-- لازم DateTime
  final int userId;
  final int domainId;
  final String? question; // Optional field for user name

  FeedbackModel({
    required this.id,
    required this.content,
    required this.rating,
    required this.createdAt,
    required this.userId,
    required this.domainId,
    required this.question,

  });

  factory FeedbackModel.fromJson(Map<String, dynamic> json) {
    return FeedbackModel(
      id: json['id'],
      content: json['content'],
      rating: json['rating'],
      createdAt: DateTime.parse(json['created_at']), // هنا التحويل
      userId: json['user_id'],
      domainId: json['domain_id'],
      question: json['question'], // Optional field
    );
  }


}
