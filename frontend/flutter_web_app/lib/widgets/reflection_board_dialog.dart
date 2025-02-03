import 'package:flutter/material.dart';
import '../services/reflection_service.dart';
import 'package:firebase_auth/firebase_auth.dart';

class ReflectionBoardDialog extends StatefulWidget {
  final List<Map<String, dynamic>> patterns;

  const ReflectionBoardDialog({
    super.key,
    required this.patterns,
  });

  @override
  State<ReflectionBoardDialog> createState() => _ReflectionBoardDialogState();
}

class _ReflectionBoardDialogState extends State<ReflectionBoardDialog> {
  late Map<String, List<Map<String, dynamic>>> _boardData;

  @override
  void initState() {
    super.initState();
    _initializeBoardData();
  }

  void _initializeBoardData() {
    _boardData = {};
    for (final pattern in widget.patterns) {
      final category = pattern['category'] as String;
      _boardData.putIfAbsent(category, () => []);
      _boardData[category]!.add(pattern);
    }
  }

  String _getCategoryDisplayName(String category) {
    switch (category.toLowerCase()) {
      case 'information_gathering':
        return '情報収集スタイル';
      case 'communication':
        return 'コミュニケーションパターン';
      case 'problem_solving':
        return '問題解決アプローチ';
      case 'learning':
        return '学習・成長パターン';
      default:
        return 'その他の特徴';
    }
  }

  Color _getCategoryColor(String category) {
    switch (category.toLowerCase()) {
      case 'information_gathering':
        return Colors.blue;
      case 'communication':
        return Colors.green;
      case 'problem_solving':
        return Colors.orange;
      case 'learning':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: _boardData.length,
      child: Dialog.fullscreen(
        child: Scaffold(
          appBar: AppBar(
            title: const Text('振り返りボード'),
            leading: IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.of(context).pop(),
            ),
            bottom: TabBar(
              isScrollable: true,
              tabs: _boardData.keys.map((category) {
                return Tab(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 4,
                        height: 24,
                        margin: const EdgeInsets.only(right: 8),
                        color: _getCategoryColor(category),
                      ),
                      Text(_getCategoryDisplayName(category)),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          body: TabBarView(
            children: _boardData.entries.map((entry) {
              final category = entry.key;
              final patterns = entry.value;
              
              return SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: patterns.map((pattern) {
                    return Card(
                      margin: const EdgeInsets.only(bottom: 16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(16.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    pattern['pattern'] ?? '',
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12.0,
                                    vertical: 6.0,
                                  ),
                                  decoration: BoxDecoration(
                                    color: _getCategoryColor(category).withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(16.0),
                                  ),
                                  child: Text(
                                    '${(pattern['confidence'] * 100).toStringAsFixed(0)}%',
                                    style: TextStyle(
                                      color: _getCategoryColor(category),
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Divider(height: 1),
                          if (pattern['examples'] != null)
                            ...pattern['examples'].map<Widget>((example) =>
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16.0,
                                  vertical: 8.0,
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      '関連する振り返り:',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.grey,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Card(
                                      color: Theme.of(context).cardColor.withOpacity(0.5),
                                      child: Padding(
                                        padding: const EdgeInsets.all(12.0),
                                        child: Text(
                                          example,
                                          style: Theme.of(context).textTheme.bodyMedium,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ).toList(),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}