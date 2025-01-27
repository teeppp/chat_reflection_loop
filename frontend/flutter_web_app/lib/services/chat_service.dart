import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';
import 'sse_stream_web.dart';

class ChatService {
  final AuthService _authService;
  final String _baseUrl;
  
  ChatService({
    required String baseUrl,
    AuthService? authService,
  }) : _baseUrl = baseUrl,
       _authService = authService ?? AuthService();

  /// 同期的なメッセージ送信
  Future<String> sendMessage(String message) async {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      final response = await http.post(
        Uri.parse('$_baseUrl/baseagent/invoke'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'message': message}),
      );

      if (response.statusCode != 200) {
        throw Exception('API エラー: ${response.statusCode} ${response.body}');
      }

      final Map<String, dynamic> data = jsonDecode(response.body);
      return data['response'] ?? 'エラー: 応答が空です';
    } catch (e) {
      throw Exception('メッセージ送信エラー: $e');
    }
  }

  /// ストリーミング応答の受信
  Stream<String> sendMessageStream(String message) async* {
    try {
      final token = await _authService.getIdToken();
      if (token == null) throw Exception('認証トークンが取得できません');

      var request = http.Request(
        'POST',
        Uri.parse('$_baseUrl/baseagent/stream'),
      );

      request.headers.addAll({
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Authorization': 'Bearer $token',
      });
      request.body = jsonEncode({'message': message});
      request.persistentConnection = false;

      var byteStream = await getStream(request);
      String? lastContent;  // 前回の内容を保持
      
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
              continue;
            }
            
            try {
              var jsonData = jsonDecode(data);
              print('JSONデータ: $jsonData');
              
              if (jsonData is Map && jsonData.containsKey('text')) {
                var newText = jsonData['text'] as String;
                print('新しいテキスト: $newText');
                print('前回のテキスト: $lastContent');
                
                if (newText != lastContent) {
                  print('テキストが更新されました');
                  lastContent = newText;
                  yield newText;
                } else {
                  print('同じテキストなのでスキップします');
                }
              }
            } catch (e) {
              print('JSON解析エラー: $e, データ: $data');
              if (data != lastContent) {
                lastContent = data;
                yield data;
              }
            }
          }
        }
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
}