class Thread {
  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;

  Thread({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Thread.fromJson(Map<String, dynamic> json) {
    return Thread(
      id: json['id'] as String,
      title: json['title'] as String? ??
        '${DateTime.parse(json['created_at'] as String).year}/' +
        '${DateTime.parse(json['created_at'] as String).month}/' +
        '${DateTime.parse(json['created_at'] as String).day}の会話',
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}