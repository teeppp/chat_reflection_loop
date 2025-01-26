import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/signup_screen.dart';
import 'screens/chat_screen.dart';

void main() async {
  try {
    await runZonedGuarded(() async {
      WidgetsFlutterBinding.ensureInitialized();
      
      print('Starting application initialization...');
      
      try {
        print('Loading environment variables...');
        await dotenv.load(fileName: ".env");
        print('Environment variables loaded successfully');
      } catch (e) {
        print('Error loading environment variables: $e');
        rethrow;
      }

      try {
        print('Initializing Firebase...');
        await Firebase.initializeApp(
          options: FirebaseOptions(
            apiKey: dotenv.env['FIREBASE_API_KEY'] ?? '',
            authDomain: dotenv.env['FIREBASE_AUTH_DOMAIN'] ?? '',
            projectId: dotenv.env['FIREBASE_PROJECT_ID'] ?? '',
            messagingSenderId: dotenv.env['FIREBASE_MESSAGING_SENDER_ID'] ?? '',
            appId: dotenv.env['FIREBASE_APP_ID'] ?? '',
          ),
        );
        print('Firebase initialization successful');
      } catch (e) {
        print('Firebase initialization error: $e');
        rethrow;
      }

      runApp(const MyApp());
    }, (error, stack) {
      print('Uncaught error: $error');
      print('Stack trace: $stack');
    });
  } catch (e) {
    print('Fatal error: $e');
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
                  return const ChatScreen();
                }

                print('User is not signed in');
                return const LoginScreen();
              },
            ),
        '/login': (context) => const LoginScreen(),
        '/signup': (context) => const SignUpScreen(),
        '/home': (context) => const ChatScreen(),
        '/debug': (context) => const HomeScreen(), // JWTトークン表示用
      },
    );
  }
}
