import 'package:firebase_auth/firebase_auth.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  // 認証状態の変更を監視するStream
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // 現在のユーザーを取得
  User? get currentUser => _auth.currentUser;

  // メール/パスワードでサインアップ (無効化)
  Future<UserCredential> signUpWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    throw Exception('セキュリティ上の理由により、サインアップ機能は無効化されています。');
  }

  // メール/パスワードでサインイン
  Future<UserCredential> signInWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    try {
      return await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    } on FirebaseAuthException catch (e) {
      throw _handleAuthError(e);
    }
  }

  // サインアウト
  Future<void> signOut() async {
    await _auth.signOut();
  }

  // JWTトークンを取得
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    try {
      return await _auth.currentUser?.getIdToken(forceRefresh);
    } on FirebaseAuthException catch (e) {
      throw _handleAuthError(e);
    }
  }

  // エラーハンドリング
  Exception _handleAuthError(FirebaseAuthException e) {
    switch (e.code) {
      case 'weak-password':
        return Exception('パスワードが弱すぎます');
      case 'email-already-in-use':
        return Exception('このメールアドレスは既に使用されています');
      case 'invalid-email':
        return Exception('無効なメールアドレスです');
      case 'operation-not-allowed':
        return Exception('この操作は許可されていません');
      case 'user-disabled':
        return Exception('このユーザーアカウントは無効化されています');
      case 'user-not-found':
        return Exception('ユーザーが見つかりません');
      case 'wrong-password':
        return Exception('パスワードが間違っています');
      case 'requires-recent-login':
        return Exception('再認証が必要です');
      case 'too-many-requests':
        return Exception('リクエストが多すぎます。しばらく待ってから再試行してください');
      default:
        return Exception('認証エラーが発生しました: ${e.message}');
    }
  }
}