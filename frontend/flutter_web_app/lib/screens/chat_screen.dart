import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import '../services/chat_service.dart';
import '../models/thread.dart';
import '../models/chat_history_entry.dart';
import '../models/message_response.dart';
import '../services/reflection_service.dart';
import '../widgets/reflection_preview_dialog.dart';
import '../widgets/user_patterns_dialog.dart';
import 'package:provider/provider.dart';
import 'package:firebase_auth/firebase_auth.dart';

class ChatScreen extends StatefulWidget {
  final ChatService chatService;
  final ReflectionService reflectionService;

  const ChatScreen({
    super.key,
    required this.chatService,
    required this.reflectionService,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  bool _isLoadingHistory = false;
  StreamSubscription? _streamSubscription;
  Thread? _currentThread;
  List<Thread> _threads = [];
  
  @override
  void initState() {
    super.initState();
    _loadThreads();
  }

  @override
  void dispose() {
    _streamSubscription?.cancel();
    _messageController.dispose();
    super.dispose();
  }

  // スレッド一覧を読み込む
  Future<void> _loadThreads() async {
    try {
      final threads = await widget.chatService.getThreads(forceRefresh: true);
      setState(() {
        _threads = threads;
        // 最新のスレッドを選択
        if (_currentThread == null && threads.isNotEmpty) {
          _currentThread = threads.first;
          _loadChatHistory();
        }
      });
    } catch (e) {
      _showError('スレッド一覧の取得に失敗しました: $e');
    }
  }

  // チャット履歴を読み込む
  Future<void> _loadChatHistory() async {
    if (_currentThread == null) return;

    setState(() => _isLoadingHistory = true);
    try {
      final history = await widget.chatService.getChatHistory(_currentThread!.id);
      setState(() {
        _messages.clear();
        _messages.addAll(
          history.map((entry) => ChatMessage(
            text: entry.message,
            isMe: entry.isMe,
            timestamp: entry.timestamp,
          )).toList(),
        );
      });
    } catch (e) {
      _showError('チャット履歴の取得に失敗しました: $e');
    } finally {
      setState(() => _isLoadingHistory = false);
    }
  }

  // 新しいスレッドを作成
  Future<void> _createNewThread() async {
    try {
      final now = DateTime.now();
      final thread = await widget.chatService.createThread(
        title: '${now.year}/${now.month}/${now.day}の会話',
      );
      setState(() {
        _threads = [thread, ..._threads];
        _currentThread = thread;
        _messages.clear();
      });
    } catch (e) {
      _showError('スレッドの作成に失敗しました: $e');
    }
  }

  // スレッドを削除
  Future<void> _deleteThread() async {
    if (_currentThread == null) return;

    final confirmDelete = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('スレッドを削除'),
          content: Text('スレッド「${_currentThread!.title}」を削除しますか？'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('キャンセル'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('削除'),
            ),
          ],
        );
      },
    );

    if (confirmDelete == true) {
      try {
        await widget.chatService.deleteThread(_currentThread!.id);
        setState(() {
          _threads.removeWhere((thread) => thread.id == _currentThread!.id);
          _currentThread = _threads.isNotEmpty ? _threads.first : null;
          _messages.clear();
        });
      } catch (e) {
        _showError('スレッドの削除に失敗しました: $e');
      }
    }
  }

  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;
    
    // スレッドがない場合は新規作成
    if (_currentThread == null) {
      await _createNewThread();
    }

    final messageText = text;
    _messageController.clear();

    // ユーザーメッセージを即時表示
    final userMessage = ChatMessage(
      text: messageText,
      isMe: true,
      timestamp: DateTime.now(),
    );
    setState(() {
      _messages.insert(0, userMessage);
      _isLoading = true;
    });

    try {
      if (_currentThread == null) {
        throw Exception('スレッドが選択されていません');
      }

      // メッセージを送信（バックエンドで自動的に履歴に追加される）
      final response = await widget.chatService.sendMessage(messageText, _currentThread!.id);
      
      // ボットの応答を即時表示
      if (response.botResponse != null) {
        final botMessage = ChatMessage(
          text: response.botResponse!,
          isMe: false,
          timestamp: DateTime.now(),
        );
        setState(() {
          _messages.insert(0, botMessage);
        });
      }

      // バックグラウンドで振り返りの更新を実行
      _updateReflectionsInBackground(
        userMessage: messageText,
        botResponse: response.botResponse,
      );

    } catch (e) {
      _showError('エラー: $e');
      // エラー時はユーザーメッセージを削除
      setState(() {
        _messages.remove(userMessage);
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _updateReflectionsInBackground({
    required String userMessage,
    String? botResponse,
  }) async {
    try {
      // ユーザーメッセージの振り返り更新
      await widget.reflectionService.updateReflection(
        threadId: _currentThread!.id,
        messageContent: userMessage,
        isUserMessage: true,
      );

      if (botResponse != null) {
        // ボットの応答に対する振り返り更新
        await widget.reflectionService.updateReflection(
          threadId: _currentThread!.id,
          messageContent: botResponse,
          isUserMessage: false,
        );

        // Firebaseから現在のユーザーIDを取得してインストラクションを更新
        final user = FirebaseAuth.instance.currentUser;
        if (user != null) {
          await widget.reflectionService.updateUserInstructions(user.uid);
        }
      }
    } catch (e) {
      print('バックグラウンドでの振り返り更新に失敗: $e');
      // バックグラウンド処理のため、ユーザーにエラーは表示しない
    }
  }

  void _showReflectionPreview() {
    if (_currentThread == null) {
      _showError('スレッドが選択されていません');
      return;
    }

    showDialog(
      context: context,
      builder: (context) => ReflectionPreviewDialog(
        threadId: _currentThread!.id,
        reflectionService: widget.reflectionService,
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('エラーが発生しました: $message'),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButton<Thread>(
              value: _currentThread,
              hint: const Text('スレッドを選択'),
              items: _threads.map((thread) {
                return DropdownMenuItem<Thread>(
                  value: thread,
                  child: Text(thread.title),
                );
              }).toList(),
              onChanged: (Thread? thread) {
                setState(() {
                  _currentThread = thread;
                  _loadChatHistory();
                });
              },
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: 'ユーザーの傾向',
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => UserPatternsDialog(
                  reflectionService: widget.reflectionService,
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: '新しい会話',
            onPressed: _createNewThread,
          ),
          IconButton(
            icon: const Icon(Icons.delete),
            tooltip: 'スレッドを削除',
            onPressed: _currentThread == null ? null : _deleteThread,
          ),
          IconButton(
            icon: const Icon(Icons.description),
            tooltip: '振り返りメモ',
            onPressed: _currentThread == null ? null : _showReflectionPreview,
          ),
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
              if (_isLoadingHistory)
                const LinearProgressIndicator(),
              Flexible(
                child: ListView.builder(
                  padding: const EdgeInsets.all(8.0),
                  reverse: true,
                  itemBuilder: (_, int index) => _buildMessage(_messages[index]),
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

  Widget _buildMessage(ChatMessage message) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            margin: const EdgeInsets.only(right: 16.0),
            child: CircleAvatar(
              backgroundColor: message.isMe ? Colors.blue : Colors.green,
              child: Text(
                message.isMe ? 'ME' : 'BOT',
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  message.isMe ? '自分' : 'ボット',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Container(
                  margin: const EdgeInsets.only(top: 5.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(message.text),
                      Text(
                        _formatTimestamp(message.timestamp),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
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
