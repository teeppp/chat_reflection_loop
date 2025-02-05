import 'package:flutter/material.dart';
import 'dart:async';
import '../services/chat_service.dart';
import '../models/thread.dart';
import '../models/message_response.dart';

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
  bool _useStream = false;
  Thread? _currentThread;
  List<Thread> _threads = [];
  StreamSubscription? _streamSubscription;

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
      final threads = await widget.chatService.getThreads();
      setState(() {
        _threads = threads;
        // 最新のスレッドを選択
        if (_currentThread == null && threads.isNotEmpty) {
          _currentThread = threads.first;
        }
      });
    } catch (e) {
      _showError('スレッド一覧の取得に失敗しました: $e');
    }
  }

  // 新しいスレッドを作成
  Future<void> _createNewThread() async {
    try {
      final thread = await widget.chatService.createThread(
        title: '新しい会話 ${DateTime.now().toString()}',
      );
      setState(() {
        _threads = [thread, ..._threads];
        _currentThread = thread;
      });
    } catch (e) {
      _showError('スレッドの作成に失敗しました: $e');
    }
  }

  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;
    
    // スレッドがない場合は新規作成
    if (_currentThread == null) {
      await _createNewThread();
    }

    setState(() {
      _isLoading = true;
      _request = text;
      _response = '';
    });

    try {
      if (_useStream) {
        await _handleStreamSubmit(text);
      } else {
        final response = await widget.chatService.sendMessage(text, _currentThread!.id);
        setState(() {
          _response = response.botResponse ?? 'エラー: 応答が空です';
          if (!response.success) {
            _showError(response.error ?? 'エラーが発生しました');
          }
        });
      }
    } catch (e) {
      _showError('エラー: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
      _messageController.clear();
    }
  }

  Future<void> _handleStreamSubmit(String text) async {
    if (_streamSubscription != null) {
      await _streamSubscription!.cancel();
    }

    try {
      final stream = widget.chatService.sendMessageStream(text, _currentThread!.id);
      _streamSubscription = stream.listen(
        (response) {
          setState(() => _response = response);
        },
        onError: (error) {
          _showError('ストリーミングエラー: $error');
        },
        onDone: () {
          setState(() => _isLoading = false);
        },
      );
    } catch (e) {
      throw Exception('ストリーミングエラー: $e');
    }
  }

  Future<void> _clearAllHistory() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('全ての履歴を削除'),
        content: const Text('本当に全てのチャット履歴を削除しますか？\nこの操作は取り消せません。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('キャンセル'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('削除'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      try {
        await widget.chatService.clearAllHistory();
        // スレッド一覧を再読み込み
        await _loadThreads();
        // 状態をリセット
        setState(() {
          _currentThread = null;
          _request = '';
          _response = '';
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('全ての履歴を削除しました')),
          );
        }
      } catch (e) {
        _showError('履歴の削除に失敗しました: $e');
      }
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
        title: DropdownButton<Thread>(
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
            });
          },
        ),
        actions: [
          // Stream/Invoke切り替えスイッチ
          Row(
            children: [
              const Text('Stream'),
              Switch(
                value: _useStream,
                onChanged: (value) => setState(() => _useStream = value),
              ),
            ],
          ),
          // 新しいスレッド作成ボタン
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: '新しい会話',
            onPressed: _createNewThread,
          ),
          // 履歴全クリアボタン
          IconButton(
            icon: const Icon(Icons.delete_forever),
            tooltip: '全ての履歴を削除',
            onPressed: _clearAllHistory,
          ),
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
          // デバッグ情報パネル
          Container(
            padding: const EdgeInsets.all(8.0),
            color: Colors.grey.shade100,
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Column(
                      children: [
                        const Text('モード'),
                        Text(
                          _useStream ? 'Stream' : 'Invoke',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    Column(
                      children: [
                        const Text('スレッド'),
                        Text(
                          _currentThread?.id.substring(0, 8) ?? 'なし',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    Column(
                      children: [
                        const Text('スレッド数'),
                        Text(
                          _threads.length.toString(),
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // リクエストカード
                  if (_request.isNotEmpty)
                    Card(
                      color: Colors.blue.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.arrow_upward, color: Colors.blue),
                                const SizedBox(width: 8),
                                const Text(
                                  'リクエスト',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(_request),
                          ],
                        ),
                      ),
                    ),
                  if (_request.isNotEmpty)
                    const SizedBox(height: 16),
                  // レスポンスカード
                  if (_response.isNotEmpty)
                    Card(
                      color: Colors.green.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.arrow_downward, color: Colors.green),
                                const SizedBox(width: 8),
                                const Text(
                                  'レスポンス',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
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
                    decoration: InputDecoration(
                      hintText: _useStream ? 'Stream メッセージを入力' : 'Invoke メッセージを入力',
                      border: const OutlineInputBorder(),
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