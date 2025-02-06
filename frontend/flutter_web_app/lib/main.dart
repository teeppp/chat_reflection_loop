import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:provider/provider.dart';
import 'package:js/js_util.dart' as js_util;
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/debug_chat_screen.dart';
import 'services/chat_service.dart';
import 'services/reflection_service.dart';
import 'config/app_config.dart';

void main() async {
  try {
    await runZonedGuarded(() async {
      WidgetsFlutterBinding.ensureInitialized();
      
      print('Starting application initialization...');
      
      try {
        print('Loading configuration...');
        // index.htmlから設定を読み込む
        final env = js_util.getProperty(js_util.getProperty(js_util.globalThis, 'window'), 'flutterWebEnvironment');
        
        // デバッグ用：読み込んだ設定を確認
        print('Loaded environment config:');
        print('apiKey: ${js_util.getProperty(env, 'apiKey')}');
        print('authDomain: ${js_util.getProperty(env, 'authDomain')}');
        print('projectId: ${js_util.getProperty(env, 'projectId')}');
        print('apiBaseUrl: ${js_util.getProperty(env, 'apiBaseUrl')}');
        
        try {
          print('Initializing Firebase...');
          await Firebase.initializeApp(
            options: FirebaseOptions(
              apiKey: js_util.getProperty(env, 'apiKey'),
              authDomain: js_util.getProperty(env, 'authDomain'),
              projectId: js_util.getProperty(env, 'projectId'),
              storageBucket: js_util.getProperty(env, 'storageBucket'),
              messagingSenderId: js_util.getProperty(env, 'messagingSenderId'),
              appId: js_util.getProperty(env, 'appId'),
              measurementId: js_util.getProperty(env, 'measurementId'),
            ),
          );
          print('Firebase initialization successful');
        } catch (e) {
          print('Firebase initialization error: $e');
          print('Firebase initialization stack trace:');
          print(StackTrace.current);
          rethrow;
        }

        final chatService = ChatService(baseUrl: js_util.getProperty(env, 'apiBaseUrl'));
        final reflectionService = ReflectionService(baseUrl: js_util.getProperty(env, 'apiBaseUrl'));

        // Firebaseの認証状態を監視し、トークンの変更を検知
        FirebaseAuth.instance.authStateChanges().listen((User? user) async {
          if (user != null) {
            try {
              final token = await user.getIdToken();
              reflectionService.authToken = token;
              print('認証トークンを設定しました');
            } catch (e) {
              print('認証トークンの取得に失敗: $e');
            }
          }
        });

        runApp(
          MultiProvider(
            providers: [
              Provider<ChatService>(
                create: (_) => chatService,
              ),
              Provider<ReflectionService>(
                create: (_) => reflectionService,
              ),
            ],
            child: const MyApp(),
          ),
        );
      } catch (e, stackTrace) {
        print('Error loading configuration: $e');
        print('Stack trace: $stackTrace');
        rethrow;
      }
    }, (error, stack) {
      print('Uncaught error: $error');
      print('Stack trace: $stack');
    });
  } catch (e, stackTrace) {
    print('Fatal error: $e');
    print('Stack trace: $stackTrace');
    rethrow;
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building MyApp widget...');
    return MaterialApp(
      title: 'Flutter Web Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => StreamBuilder<User?>(
              stream: FirebaseAuth.instance.authStateChanges(),
              builder: (context, snapshot) {
                print('Auth state changed: ${snapshot.connectionState}');

                if (snapshot.hasError) {
                  print('Auth error: ${snapshot.error}');
                  return Scaffold(
                    body: Center(
                      child: Text('エラーが発生しました: ${snapshot.error}'),
                    ),
                  );
                }

                if (snapshot.connectionState == ConnectionState.waiting) {
                  print('Waiting for auth state...');
                  return const Scaffold(
                    body: Center(
                      child: CircularProgressIndicator(),
                    ),
                  );
                }

                if (snapshot.hasData) {
                  print('User is signed in');
                  return ChatScreen(
                    chatService: Provider.of<ChatService>(context),
                    reflectionService: Provider.of<ReflectionService>(context),
                  );
                }

                print('User is not signed in');
                return const LoginScreen();
              },
            ),
        '/login': (context) => const LoginScreen(),
        '/home': (context) => ChatScreen(
              chatService: Provider.of<ChatService>(context),
              reflectionService: Provider.of<ReflectionService>(context),
            ),
        '/debug': (context) => const HomeScreen(), // JWTトークン表示用
        '/debug-chat': (context) => DebugChatScreen(chatService: Provider.of<ChatService>(context)), // デバッグチャット画面
      },
    );
  }
}
