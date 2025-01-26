import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];

  void _handleSubmitted(String text) {
    _messageController.clear();
    ChatMessage message = ChatMessage(
      text: text,
      isMe: true,
    );
    setState(() {
      _messages.insert(0, message);
    });
    // TODO: Mockの応答を返す処理を実装
    Future.delayed(const Duration(milliseconds: 500), () {
      ChatMessage botMessage = ChatMessage(
        text: 'ボットの応答: $text', // Mockの応答
        isMe: false,
      );
      setState(() {
        _messages.insert(0, botMessage);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('チャット'),
        actions: kDebugMode
            ? [
                IconButton(
                  icon: const Icon(Icons.bug_report),
                  tooltip: 'デバッグ画面',
                  onPressed: () => Navigator.pushNamed(context, '/debug'),
                ),
              ]
            : null,
      ),
      body: Column(
        children: <Widget>[
          Flexible(
            child: ListView.builder(
              padding: const EdgeInsets.all(8.0),
              reverse: true,
              itemBuilder: (BuildContext context, int index) => _messages[index],
              itemCount: _messages.length,
            ),
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
                decoration: const InputDecoration.collapsed(
                  hintText: 'メッセージを送信',
                ),
              ),
            ),
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 4.0),
              child: IconButton(
                icon: const Icon(Icons.send),
                onPressed: () => _handleSubmitted(_messageController.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatMessage extends StatelessWidget {
  ChatMessage({
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
            child: CircleAvatar(child: Text(isMe ? 'ME' : 'BOT')), // アイコンをMEとBOTで変更
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(isMe ? '自分' : 'ボット', style: Theme.of(context).textTheme.titleMedium), // 名前をMEとBOTで変更
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
