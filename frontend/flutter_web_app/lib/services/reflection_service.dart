import 'dart:convert' show jsonEncode, jsonDecode, utf8;
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ReflectionException implements Exception {
  final String message;
  final String? code;

  ReflectionException(this.message, {this.code});

  @override
  String toString() => 'ReflectionException: $message ${code ?? ""}';
}

class ReflectionService {
  final String baseUrl;
  String? _authToken;
  final http.Client _client;

  ReflectionService({
    String? baseUrl,
    String? authToken,
    http.Client? client,
  })  : baseUrl = baseUrl ?? dotenv.env['API_BASE_URL'] ?? 'http://localhost:8080',
        _authToken = authToken,
        _client = client ?? http.Client();

  set authToken(String? value) {
    _authToken = value;
  }

  String? get authToken => _authToken;

  Map<String, String> get _headers {
    if (_authToken == null || _authToken!.isEmpty) {
      throw ReflectionException('認証トークンが設定されていません');
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $_authToken',
    };
  }

  /// 振り返りの更新
  Future<void> updateReflection({
    required String threadId,
    required String messageContent,
    required bool isUserMessage,
  }) async {
    try {
      final requestBody = {
        'session_id': threadId,
        'user_id': null,  // バックエンドでFirebaseトークンから取得
      };
      print('Reflection生成リクエスト: $requestBody');

      final response = await _client.post(
        Uri.parse('$baseUrl/api/v1/reflections/generate'),
        headers: _headers,
        body: utf8.encode(jsonEncode(requestBody)),
      );

      print('Reflectionレスポンス: ${utf8.decode(response.bodyBytes)}');

      if (response.statusCode != 200) {
        throw ReflectionException(
          '振り返りの更新に失敗しました',
          code: response.statusCode.toString(),
        );
      }
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException('振り返りの更新中にエラーが発生しました: $e');
    }
  }

  /// 振り返りメモの取得
  /// ユーザーの傾向を取得（振り返りノートから分析）
  Future<List<Map<String, dynamic>>> getUserPatterns(String userId) async {
    try {
      print('ユーザー傾向分析を開始: $userId');

      // 振り返りノートの分析を要求
      final response = await _client.post(
        Uri.parse('$baseUrl/api/v1/profiles/$userId/analyze-reflection'),
        headers: {
          ..._headers,
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'content': '',  // 空のコンテンツ（バックエンドで振り返りを取得）
          'analyze_type': 'all_reflections',  // 全ての振り返りノートを分析
          'task_name': 'ユーザー傾向分析',
          'created_at': DateTime.now().toIso8601String(),
        }),
      );

      print('ユーザー傾向レスポンス: ${utf8.decode(response.bodyBytes)}');

      if (response.statusCode != 200) {
        throw ReflectionException(
          'ユーザー傾向の取得に失敗しました',
          code: response.statusCode.toString(),
        );
      }

      final responseText = utf8.decode(response.bodyBytes);
      print('APIレスポンス: $responseText');
      
      final data = jsonDecode(responseText);
      if (data is String) {
        // 文字列の場合はパターンとして解釈
        return [
          {
            'label': 'システム分析',
            'description': data,
            'confidence': 1.0
          }
        ];
      }
      
      final patterns = data['patterns'];
      if (patterns == null) {
        return [];
      }
      
      return List<Map<String, dynamic>>.from(patterns);
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException('ユーザー傾向の取得中にエラーが発生しました: $e');
    }
  }

  Future<String> getReflectionMemo(String threadId) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/api/v1/reflections/session/$threadId'),
        headers: _headers,
      );

      if (response.statusCode != 200) {
        throw ReflectionException(
          '振り返りメモの取得に失敗しました',
          code: response.statusCode.toString(),
        );
      }

      final data = jsonDecode(utf8.decode(response.bodyBytes));
      final reflection = data['reflection'];
      return (reflection['content'] ?? '') as String;
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException('振り返りメモの取得中にエラーが発生しました: $e');
    }
  }

  /// ユーザーインストラクションの更新
  Future<void> updateUserInstructions(String userId) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/api/v1/profiles/$userId/instructions/code'),
        headers: _headers,
      );

      if (response.statusCode != 200) {
        throw ReflectionException(
          'ユーザーインストラクションの更新に失敗しました',
          code: response.statusCode.toString(),
        );
      }

      final data = jsonDecode(response.body);
      print('ユーザーインストラクションを更新しました: ${data['instructions']}');
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException(
          'ユーザーインストラクションの更新中にエラーが発生しました: $e');
    }
  }

  /// リソースの解放
  void dispose() {
    _client.close();
  }
}