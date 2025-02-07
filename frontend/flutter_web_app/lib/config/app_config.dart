import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  static Future<void> load() async {
    if (!kIsWeb) {
      // モバイル環境ではJSON設定ファイルを使用
      try {
        final String configString = await rootBundle.loadString('assets/config/config_dev.json');
        final Map<String, dynamic> config = json.decode(configString);
        
        // 環境変数として設定
        dotenv.env['FIREBASE_API_KEY'] = config['firebase']['apiKey'];
        dotenv.env['FIREBASE_AUTH_DOMAIN'] = config['firebase']['authDomain'];
        dotenv.env['FIREBASE_PROJECT_ID'] = config['firebase']['projectId'];
        dotenv.env['FIREBASE_MESSAGING_SENDER_ID'] = config['firebase']['messagingSenderId'];
        dotenv.env['FIREBASE_APP_ID'] = config['firebase']['appId'];
        dotenv.env['API_BASE_URL'] = config['api']['baseUrl'];
      } catch (e) {
        print('設定ファイルの読み込みエラー: $e');
        rethrow;
      }
    }
  }
}