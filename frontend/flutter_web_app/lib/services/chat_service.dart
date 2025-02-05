import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/thread.dart';
import '../models/chat_history_entry.dart';
import '../models/message_response.dart';
import 'auth_service.dart';
import 'sse_stream_web.dart';

class ChatService {
  /// キャッシュされたスレッド一覧
  List<Thread>? _cachedThreads;
  DateTime? _lastThreadsFetch;
  final AuthService _authService;
  final String _baseUrl;
  
  ChatService({
    required String baseUrl,
    AuthService? authService,
  }) : _baseUrl = baseUrl,
       _authService = authService ?? AuthService();

  /// 同期的なメッセージ送信
  Future<MessageResponse> sendMessage(String message, String threadId) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.post(
        Uri.parse('$_baseUrl/baseagent/invoke'),
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Accept': 'application/json; charset=utf-8',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'message': message,
          'thread_id': threadId,
        }),
      );

      if (response.statusCode != 200) {
        return MessageResponse.error('API エラー: ${response.statusCode} ${response.body}');
      }

      final Map<String, dynamic> data = jsonDecode(response.body);
      final botResponse = data['response'];
      if (botResponse == null) {
        return MessageResponse.error('エラー: 応答が空です');
      }
      return MessageResponse.success(botResponse);
    } catch (e) {
      return MessageResponse.error('メッセージ送信エラー: $e');
    }
  }

  /// メッセージを追加
  Future<void> addMessage(String sessionId, String message, bool isUserMessage) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.put(
        Uri.parse('$_baseUrl/api/v1/chat-histories/$sessionId'),
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'role': isUserMessage ? 'user' : 'assistant',
          'content': message,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }
    } catch (e) {
      throw Exception('メッセージ追加エラー: $e');
    }
  }

  /// ストリーミング応答の受信と保存
  Stream<String> sendMessageStream(String message, String sessionId) async* {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      // ユーザーメッセージを保存
      await addMessage(sessionId, message, true);

      final url = Uri.parse('$_baseUrl/baseagent/stream');
      final request = http.Request('POST', url)
        ..headers.addAll({
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Authorization': 'Bearer $token',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        })
        ..body = jsonEncode({'message': message});

      var byteStream = await getStream(request);
      String? lastContent;  // 前回の内容を保持
      String? finalResponse;
      bool isDone = false;
      
      await for (var bytes in byteStream) {
        print('受信したバイトデータ: ${bytes.length} bytes');
        var lines = const Utf8Decoder().convert(bytes).split('\n');
        print('分割された行数: ${lines.length}');
        
        for (var line in lines) {
          if (line.trim().isEmpty) continue;
          print('処理中の行: $line');
          
          if (line.startsWith('data: ')) {
            var data = line.substring(6).trim();
            print('抽出したデータ: $data');
            
            if (data == '[DONE]') {
              print('終了マーカーを検出');
              isDone = true;
              continue;
            }
            
            try {
              var jsonData = jsonDecode(data);
              print('JSONデータ: $jsonData');
              
              if (jsonData is Map && jsonData.containsKey('text')) {
                var newText = jsonData['text'] as String;
                print('新しいテキスト: $newText');
                
                if (newText != lastContent) {
                  print('テキストが更新されました');
                  lastContent = newText;
                  finalResponse = newText; // 最後のレスポンスを保持
                  yield newText;
                }
              }
            } catch (e) {
              print('JSON解析エラー: $e, データ: $data');
              if (data != lastContent) {
                lastContent = data;
                finalResponse = data;
                yield data;
              }
            }
          }
        }
      }
      
      // ストリーミング完了後、最終応答を保存
      if (finalResponse != null) {
        print('ストリーミング完了後、応答を保存: $finalResponse');
        await addMessage(sessionId, finalResponse, false);
      }
    } catch (e) {
      throw Exception('ストリーミング エラー: $e');
    }
  }

  /// ヘルスチェック
  Future<bool> checkHealth() async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.get(
        Uri.parse('$_baseUrl/health'),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// スレッド一覧を取得
  /// キャッシュがある場合は5分以内であればキャッシュを返す
  Future<List<Thread>> getThreads({bool forceRefresh = false}) async {
    // キャッシュチェック
    if (!forceRefresh &&
        _cachedThreads != null &&
        _lastThreadsFetch != null &&
        DateTime.now().difference(_lastThreadsFetch!) < const Duration(minutes: 5)) {
      return _cachedThreads!;
    }

    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/chat-histories'),
        headers: {
          'Accept': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }

      final Map<String, dynamic> responseData = jsonDecode(response.body);
      final List<dynamic> histories = responseData['histories'];
      _cachedThreads = histories.map((json) => Thread.fromJson({
        'id': json['session_id'],
        'title': json['title'] ?? _createThreadTitle(DateTime.parse(json['created_at'] as String)),
        'created_at': json['created_at'],
        'updated_at': json['updated_at'] ?? json['created_at'],
      })).toList();
      _lastThreadsFetch = DateTime.now();
      return _cachedThreads!;
    } catch (e) {
      _cachedThreads = null; // エラー時にキャッシュをクリア
      if (e is http.ClientException) {
        throw Exception('スレッド一覧取得エラー: ${e.message}');
      } else {
        throw Exception('スレッド一覧取得エラー: $e');
      }
    }
  }

  /// 特定のスレッドのチャット履歴を取得
  Future<List<ChatHistoryEntry>> getChatHistory(String threadId) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/chat-histories/$threadId'),
        headers: {
          'Accept': 'application/json; charset=utf-8',
          'Authorization': 'Bearer $token',
        },
      );

      // レスポンスヘッダーから文字エンコーディングを確認
      print('Content-Type: ${response.headers['content-type']}');
      
      // 明示的にUTF-8でデコード
      final responseBody = utf8.decode(response.bodyBytes);

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }

      final Map<String, dynamic> responseData = jsonDecode(responseBody);
      final Map<String, dynamic> history = responseData['history'];
      final List<dynamic> messages = history['messages'];
      
      return messages.map((json) => ChatHistoryEntry.fromJson({
        'message': json['content'],
        'is_user': json['role'] == 'user',
        'timestamp': json['timestamp'],
        'message_id': json['id'] ?? DateTime.now().toIso8601String(),
        'thread_id': threadId,
      })).toList();
    } catch (e) {
      throw Exception('チャット履歴取得エラー: $e');
    }
  }

  /// 新しいスレッドを作成
  Future<Thread> createThread({String? title}) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/chat-histories'),
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Accept': 'application/json; charset=utf-8',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'initial_message': null,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }

      final Map<String, dynamic> responseData = jsonDecode(response.body);
      final now = DateTime.now();
      final newThread = Thread(
        id: responseData['session_id'],
        title: title ?? _createThreadTitle(now),
        createdAt: now,
        updatedAt: now,
      );
      
      // キャッシュを更新
      _cachedThreads = [...?_cachedThreads, newThread];
      _lastThreadsFetch = DateTime.now();
      
      return newThread;
    } catch (e) {
      throw Exception('スレッド作成エラー: $e');
    }
  }

  /// スレッドのタイトルを生成
  String _createThreadTitle(DateTime date) {
    return '${date.year}/${date.month}/${date.day} ' +
           '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}の会話';
  }

  /// 全ての履歴を削除
  Future<void> clearAllHistory() async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.delete(
        Uri.parse('$_baseUrl/api/v1/chat-histories/clear'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }

      // キャッシュをクリア
      _cachedThreads = null;
      _lastThreadsFetch = null;
    } catch (e) {
      throw Exception('履歴クリアエラー: $e');
    }
  }

  /// スレッドを削除
  Future<void> deleteThread(String threadId) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      print('Deleting thread with ID: $threadId'); // デバッグログ

      final response = await http.delete(
        Uri.parse('$_baseUrl/api/v1/chat-histories/$threadId'),
        headers: {
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
        },
      );

      print('Delete response: ${response.statusCode} ${response.body}'); // デバッグログ

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }
      
      // キャッシュを更新
      _cachedThreads = null;
      _lastThreadsFetch = DateTime.now();
    } catch (e) {
      throw Exception('スレッド削除エラー: $e');
    }
  }
}