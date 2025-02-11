import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:provider/provider.dart';
import 'utils/firebase_initializer.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/debug_chat_screen.dart';
import 'services/chat_service.dart';
import 'services/reflection_service.dart';
import 'config/app_config.dart';

class AppConfig {
  static Map<String, dynamic>? _config;
  static Map<String, dynamic> get config => _config ?? {};

  static Future<void> load() async {
    try {
      final String configPath = kIsWeb
          ? 'assets/config/config.json'
          : 'android/app/src/main/assets/config.json';
          
      print('Loading config from: $configPath');
      final String configString = await rootBundle.loadString(configPath);
      _config = json.decode(configString);
      print('Config loaded successfully');
      print('Firebase Config:');
      print('apiKey: ${_config!['firebase']['apiKey']}');
      print('authDomain: ${_config!['firebase']['authDomain']}');
      print('projectId: ${_config!['firebase']['projectId']}');
      print('storageBucket: ${_config!['firebase']['storageBucket']}');
      print('messagingSenderId: ${_config!['firebase']['messagingSenderId']}');
      print('appId: ${_config!['firebase']['appId']}');
      print('measurementId: ${_config!['firebase']['measurementId']}');
      print('API Base URL: ${_config!['api']['baseUrl']}');
    } catch (e, stackTrace) {
      print('Error loading config: $e');
      print('Stack trace: $stackTrace');
      rethrow;
    }
  }
}

class ServiceInitializer extends StatefulWidget {
  final Widget child;

  const ServiceInitializer({super.key, required this.child});

  @override
  State<ServiceInitializer> createState() => _ServiceInitializerState();
}

class _ServiceInitializerState extends State<ServiceInitializer> {
  bool _initialized = false;
  bool _error = false;
  late ChatService _chatService;
  late ReflectionService _reflectionService;

  Future<void> initializeServices() async {
    try {
      if (!_initialized) {
        print('Starting Firebase initialization...');
        await FirebaseInitializer.initialize(
          apiKey: AppConfig.config['firebase']['apiKey'],
          authDomain: AppConfig.config['firebase']['authDomain'],
          projectId: AppConfig.config['firebase']['projectId'],
          storageBucket: AppConfig.config['firebase']['storageBucket'],
          messagingSenderId: AppConfig.config['firebase']['messagingSenderId'] ?? '',
          appId: AppConfig.config['firebase']['appId'],
          measurementId: AppConfig.config['firebase']['measurementId'] ?? '',
        );

        // サービスの初期化
        _chatService = ChatService(baseUrl: AppConfig.config['api']['baseUrl']);
        _reflectionService = ReflectionService(baseUrl: AppConfig.config['api']['baseUrl']);

        // Firebase認証の監視設定
        final auth = FirebaseInitializer.getAuth();
        if (auth != null) {
          auth.authStateChanges().listen((User? user) async {
            if (user != null) {
              try {
                final token = await user.getIdToken();
                _reflectionService.authToken = token;
                print('認証トークンを設定しました');
              } catch (e) {
                print('認証トークンの取得に失敗: $e');
              }
            }
          });
        }

        setState(() {
          _initialized = true;
        });
      }
    } catch (e) {
      print('Service initialization error: $e');
      setState(() {
        _error = true;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    initializeServices();
  }

  @override
  Widget build(BuildContext context) {
    if (_error) {
      return MaterialApp(
        home: Scaffold(
          body: Center(
            child: Text('初期化エラー\nアプリを再起動してください'),
          ),
        ),
      );
    }

    if (!_initialized) {
      return MaterialApp(
        home: Scaffold(
          body: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    return MultiProvider(
      providers: [
        Provider<ChatService>(
          create: (_) => _chatService,
        ),
        Provider<ReflectionService>(
          create: (_) => _reflectionService,
        ),
      ],
      child: widget.child,
    );
  }
}

void main() async {
  try {
    await runZonedGuarded(() async {
      WidgetsFlutterBinding.ensureInitialized();
      
      print('Starting application initialization...');
      
      try {
        await AppConfig.load();
        
        runApp(
          ServiceInitializer(
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
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building MyApp widget...');
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/': (context) {
          final auth = FirebaseInitializer.getAuth();
          if (auth == null) {
            return const Scaffold(
              body: Center(
                child: Text('Firebase初期化エラー'),
              ),
            );
          }
          return StreamBuilder<User?>(
            stream: auth.authStateChanges(),
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                print('Auth error: ${snapshot.error}');
                return Scaffold(
                  body: Center(
                    child: Text('エラーが発生しました: ${snapshot.error}'),
                  ),
                );
              }

              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Scaffold(
                  body: Center(
                    child: CircularProgressIndicator(),
                  ),
                );
              }

              if (snapshot.hasData) {
                return ChatScreen(
                  chatService: Provider.of<ChatService>(context),
                  reflectionService: Provider.of<ReflectionService>(context),
                );
              }

              return const LoginScreen();
            },
          );
        },
        '/login': (context) => const LoginScreen(),
        '/home': (context) => ChatScreen(
              chatService: Provider.of<ChatService>(context),
              reflectionService: Provider.of<ReflectionService>(context),
            ),
        '/debug': (context) => const HomeScreen(),
        '/debug-chat': (context) => DebugChatScreen(
              chatService: Provider.of<ChatService>(context),
            ),
      },
    );
  }
}
