class ChatHistoryEntry {
  final String message;
  final bool isMe;
  final DateTime timestamp;
  final String messageId;
  final String? threadId;

  ChatHistoryEntry({
    required this.message,
    required this.isMe,
    required this.timestamp,
    required this.messageId,
    this.threadId,
  });

  factory ChatHistoryEntry.fromJson(Map<String, dynamic> json) {
    return ChatHistoryEntry(
      message: json['text'] as String? ?? json['message'] as String,
      isMe: json['is_user'] as bool? ?? false,
      timestamp: DateTime.parse(json['timestamp'] as String),
      messageId: json['message_id'] as String,
      threadId: json['thread_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'message': message,
      'is_user': isMe,
      'timestamp': timestamp.toIso8601String(),
      'message_id': messageId,
      if (threadId != null) 'thread_id': threadId,
    };
  }

  // ChatMessageに変換するメソッド
  ChatMessage toChatMessage() {
    return ChatMessage(
      text: message,
      isMe: isMe,
      timestamp: timestamp,
    );
  }
}

// ChatScreenで使用するメッセージウィジェット用のクラス
class ChatMessage {
  final String text;
  final bool isMe;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isMe,
    required this.timestamp,
  });
}