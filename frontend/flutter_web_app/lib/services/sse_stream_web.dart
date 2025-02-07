import 'package:fetch_client/fetch_client.dart';
import 'package:http/http.dart' as http;

Future<http.ByteStream> getStream(http.Request request) async {
  final fetchClient = FetchClient(mode: RequestMode.cors);
  final response = await fetchClient.send(request);
  return response.stream;
}