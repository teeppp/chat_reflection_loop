import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';

class FirebaseInitializer {
  static FirebaseApp? _app;
  static bool _initialized = false;

  static Future<FirebaseApp> initialize({
    required String apiKey,
    required String authDomain,
    required String projectId,
    required String storageBucket,
    required String messagingSenderId,
    required String appId,
    required String measurementId,
  }) async {
    if (_initialized) {
      print('Firebaseは既に初期化されています');
      return Firebase.app();
    }

    print('Firebaseを初期化します');
    final options = FirebaseOptions(
      apiKey: apiKey,
      authDomain: authDomain,
      projectId: projectId,
      storageBucket: storageBucket,
      messagingSenderId: messagingSenderId,
      appId: appId,
      measurementId: measurementId,
    );

    try {
      _app = await Firebase.initializeApp(options: options);
      _initialized = true;
      print('Firebaseの初期化が完了しました: ${_app?.name}');
      return _app!;
    } catch (e) {
      print('Firebase初期化エラー: $e');
      rethrow;
    }
  }

  static FirebaseAuth? getAuth() {
    if (!_initialized || _app == null) {
      print('FirebaseAuth取得エラー: Firebaseが初期化されていません');
      return null;
    }

    try {
      return FirebaseAuth.instanceFor(app: _app!);
    } catch (e) {
      print('FirebaseAuth取得エラー: $e');
      return null;
    }
  }
}
