class MessageResponse {
  final String? botResponse;
  final bool success;
  final String? error;

  MessageResponse({
    this.botResponse,
    this.success = true,
    this.error,
  });

  factory MessageResponse.success(String response) {
    return MessageResponse(
      botResponse: response,
      success: true,
    );
  }

  factory MessageResponse.error(String errorMessage) {
    return MessageResponse(
      success: false,
      error: errorMessage,
    );
  }
}