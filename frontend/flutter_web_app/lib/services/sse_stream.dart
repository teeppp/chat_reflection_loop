import 'package:flutter/foundation.dart' show kIsWeb;

export 'sse_stream_mobile.dart' if (dart.library.html) 'sse_stream_web.dart';