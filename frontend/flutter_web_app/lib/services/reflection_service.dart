import 'dart:convert' show jsonEncode, jsonDecode, utf8;
import 'dart:math' show min;
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

  /// ユーザーの傾向を更新（分析を実行）
  Future<void> analyzeUserPatterns(
    String userId, {
    String? content,
    bool forceUpdate = false,
  }) async {
    try {
      print('ユーザー傾向分析を開始: $userId');
      print('振り返り内容: ${content != null ? content.substring(0, min(100, content.length)) : "なし"}');

      // 振り返りノートの分析を要求
      final response = await _client.post(
        Uri.parse('$baseUrl/api/v1/profiles/$userId/analyze'),
        headers: _headers,
        body: jsonEncode({
          'content': content,
          'force_update': forceUpdate,
        }),
      );

      print('分析レスポンス: ${utf8.decode(response.bodyBytes)}');

      if (response.statusCode != 200) {
        throw ReflectionException(
          'ユーザー傾向の分析に失敗しました',
          code: response.statusCode.toString(),
        );
      }

      // 分析完了後、結果を取得
      await getUserPatterns(userId);
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException('ユーザー傾向の分析中にエラーが発生しました: $e');
    }
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

  /// ユーザープロファイル分析結果を取得
  Future<Map<String, dynamic>> getUserPatterns(String userId) async {
    try {
      print('ユーザー傾向分析を取得: $userId');

      // 分析結果を取得
      final response = await _client.get(
        Uri.parse('$baseUrl/api/v1/profiles/$userId/analysis'),
        headers: _headers,
      );

      if (response.statusCode != 200) {
        throw ReflectionException(
          'ユーザー傾向の取得に失敗しました',
          code: response.statusCode.toString(),
        );
      }

      final responseText = utf8.decode(response.bodyBytes);
      print('プロファイル分析レスポンス: $responseText');
      
      final data = jsonDecode(responseText);
      if (data == null) {
        return {
          'patterns': [],
          'labels': [],
          'clusters': [],
          'error': 'プロファイルが見つかりません'
        };
      }

      // パターン、ラベル、クラスターを含む完全なレスポンスを返す
      return {
        'patterns': (data['patterns'] as List? ?? []).map((p) => {
          'pattern': p['pattern'],
          'category': p['category'],
          'confidence': p['confidence'],
          'detected_at': p['detected_at'],
          'context': p['context'] ?? []
        }).toList(),
        'labels': (data['labels'] as List? ?? []).map((l) => {
          'text': l['text'],
          'confidence': l['confidence'] ?? 1.0,
          'context': l['context'] ?? []
        }).toList(),
        'clusters': (data['clusters'] as List? ?? []).map((c) => {
          'cluster_id': c['cluster_id'],
          'theme': c['theme'],
          'labels': c['labels'] ?? [],
          'strength': c['strength'] ?? 1.0
        }).toList(),
        'error_occurred': data['error_occurred'] ?? false,
        'error_message': data['error_message'],
        'timestamp': data['timestamp']
      };
    } catch (e) {
      if (e is ReflectionException) rethrow;
      throw ReflectionException('ユーザー傾向の取得中にエラーが発生しました: $e');
    }
  }

  /// 振り返りメモの取得
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