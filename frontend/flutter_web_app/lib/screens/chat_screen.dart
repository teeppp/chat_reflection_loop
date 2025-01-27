import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import '../services/chat_service.dart';
import 'package:provider/provider.dart';

class ChatScreen extends StatefulWidget {
  final ChatService chatService;

  const ChatScreen({
    super.key,
    required this.chatService,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  StreamSubscription? _streamSubscription;

  @override
  void dispose() {
    _streamSubscription?.cancel();
    super.dispose();
  }

  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;
    
    _messageController.clear();
    ChatMessage message = ChatMessage(
      text: text,
      isMe: true,
    );
    setState(() {
      _messages.insert(0, message);
      _isLoading = true;
    });

    try {
      // ストリーミングレスポンスを受信
      _streamSubscription?.cancel();
      
      // 空のボットメッセージを先に挿入
      setState(() {
        _messages.insert(0, ChatMessage(
          text: '',
          isMe: false,
        ));
      });

      // ストリームを購読して逐次更新
      final stream = widget.chatService.sendMessageStream(text);
      _streamSubscription = stream.listen(
        (response) {
          print('受信したレスポンス: $response');
          if (mounted) {
            setState(() {
              // 受信したレスポンスで最新のボットメッセージを更新
              // 新しいメッセージとして直接設定
              _messages[0] = ChatMessage(
                text: response,
                isMe: false,
              );
            });
          }
        },
        onError: (error) {
          _showError('ストリーミングエラー: $error');
        },
        onDone: () {
          setState(() => _isLoading = false);
        },
      );
    } catch (e) {
      _showError('エラー: $e');
      setState(() => _isLoading = false);
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
        title: const Text('チャット'),
        actions: [
          if (kDebugMode) ...[
            IconButton(
              icon: const Icon(Icons.token),
              tooltip: 'トークン表示',
              onPressed: () => Navigator.pushNamed(context, '/debug'),
            ),
            IconButton(
              icon: const Icon(Icons.bug_report),
              tooltip: 'デバッグチャット',
              onPressed: () => Navigator.pushNamed(context, '/debug-chat'),
            ),
          ],
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
      body: Stack(
        children: [
          Column(
            children: <Widget>[
              Flexible(
                child: ListView.builder(
                  padding: const EdgeInsets.all(8.0),
                  reverse: true,
                  itemBuilder: (BuildContext context, int index) => _messages[index],
                  itemCount: _messages.length,
                ),
              ),
              if (_isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.0),
                  child: LinearProgressIndicator(),
                ),
              const Divider(height: 1.0),
              Container(
                decoration: BoxDecoration(
                  color: Theme.of(context).cardColor,
                ),
                child: _buildTextComposer(),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTextComposer() {
    return IconTheme(
      data: IconThemeData(color: Theme.of(context).colorScheme.secondary),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8.0),
        child: Row(
          children: <Widget>[
            Flexible(
              child: TextField(
                controller: _messageController,
                onSubmitted: _handleSubmitted,
                enabled: !_isLoading,
                decoration: InputDecoration.collapsed(
                  hintText: _isLoading ? '応答待ち...' : 'メッセージを送信',
                ),
              ),
            ),
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 4.0),
              child: IconButton(
                icon: const Icon(Icons.send),
                onPressed: _isLoading ? null : () => _handleSubmitted(_messageController.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatMessage extends StatelessWidget {
  const ChatMessage({
    super.key,
    required this.text,
    required this.isMe,
  });

  final String text;
  final bool isMe;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            margin: const EdgeInsets.only(right: 16.0),
            child: CircleAvatar(
              backgroundColor: isMe ? Colors.blue : Colors.green,
              child: Text(
                isMe ? 'ME' : 'BOT',
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  isMe ? '自分' : 'ボット',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Container(
                  margin: const EdgeInsets.only(top: 5.0),
                  child: Text(text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
