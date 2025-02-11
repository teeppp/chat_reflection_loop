import 'dart:convert';
import 'package:flutter/services.dart';

Future<Map<String, dynamic>> loadWebConfig() async {
  try {
    final String configString =
        await rootBundle.loadString('assets/config.json');
    return json.decode(configString);
  } catch (e) {
    print('Error loading mobile config: $e');
    rethrow;
  }
}