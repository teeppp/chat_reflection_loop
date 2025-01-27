import 'package:flutter/material.dart';
import '../services/chat_service.dart';

class DebugChatScreen extends StatefulWidget {
  final ChatService chatService;

  const DebugChatScreen({
    super.key,
    required this.chatService,
  });

  @override
  State<DebugChatScreen> createState() => _DebugChatScreenState();
}

class _DebugChatScreenState extends State<DebugChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  String _request = '';
  String _response = '';
  bool _isLoading = false;

  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;
    
    setState(() {
      _isLoading = true;
      _request = text;
      _response = '';
    });

    try {
      final response = await widget.chatService.sendMessage(text);
      setState(() {
        _response = response;
      });
    } catch (e) {
      _showError('エラー: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
      _messageController.clear();
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('デバッグチャット'),
        actions: [
          // APIの接続状態を表示
          FutureBuilder<bool>(
            future: widget.chatService.checkHealth(),
            builder: (context, snapshot) {
              final isConnected = snapshot.data ?? false;
              return Padding(
                padding: const EdgeInsets.all(8.0),
                child: Icon(
                  isConnected ? Icons.cloud_done : Icons.cloud_off,
                  color: isConnected ? Colors.green : Colors.red,
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_request.isNotEmpty)
                    Card(
                      color: Colors.blue.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              '入力メッセージ:',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(_request),
                          ],
                        ),
                      ),
                    ),
                  if (_request.isNotEmpty)
                    const SizedBox(height: 16),
                  if (_response.isNotEmpty)
                    Card(
                      color: Colors.green.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'レスポンス:',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(_response),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8.0),
              child: LinearProgressIndicator(),
            ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: 'メッセージを入力',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: _handleSubmitted,
                    enabled: !_isLoading,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _isLoading
                      ? null
                      : () => _handleSubmitted(_messageController.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}