@JS('web_config')
library web_config;

import 'package:js/js.dart';
import 'package:js/js_util.dart' as js_util;

Future<Map<String, dynamic>> loadWebConfig() async {
  try {
    final env = js_util.getProperty(
        js_util.getProperty(js_util.globalThis, 'window'),
        'flutterWebEnvironment');
    return {
      'firebase': {
        'apiKey': js_util.getProperty(env, 'apiKey'),
        'authDomain': js_util.getProperty(env, 'authDomain'),
        'projectId': js_util.getProperty(env, 'projectId'),
        'storageBucket': js_util.getProperty(env, 'storageBucket'),
        'messagingSenderId': js_util.getProperty(env, 'messagingSenderId'),
        'appId': js_util.getProperty(env, 'appId'),
        'measurementId': js_util.getProperty(env, 'measurementId'),
      },
      'api': {
        'baseUrl': js_util.getProperty(env, 'apiBaseUrl'),
      },
    };
  } catch (e) {
    print('Error loading web config: $e');
    rethrow;
  }
}