import 'package:http/http.dart' as http;

Future<http.ByteStream> getStream(http.Request request) async {
  final client = http.Client();
  final response = await client.send(request);
  return response.stream;
}