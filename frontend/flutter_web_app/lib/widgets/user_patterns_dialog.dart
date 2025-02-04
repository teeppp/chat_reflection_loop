import 'package:flutter/material.dart';
import '../services/reflection_service.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'reflection_board_dialog.dart';

class UserPatternsDialog extends StatefulWidget {
  final ReflectionService reflectionService;

  const UserPatternsDialog({
    super.key,
    required this.reflectionService,
  });

  @override
  State<UserPatternsDialog> createState() => _UserPatternsDialogState();
}

class _UserPatternsDialogState extends State<UserPatternsDialog> {
  late Future<List<Map<String, dynamic>>> _patternsFuture;

  @override
  void initState() {
    super.initState();
    _loadPatterns();
  }

  void _loadPatterns() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _patternsFuture = Future.error('ユーザーが認証されていません');
      });
      return;
    }

    setState(() {
      _patternsFuture = widget.reflectionService.getUserPatterns(user.uid);
    });
  }

  // パターンをカテゴリごとにグループ化
  Map<String, List<Map<String, dynamic>>> _groupPatternsByCategory(List<Map<String, dynamic>> patterns) {
    final grouped = <String, List<Map<String, dynamic>>>{};
    for (final pattern in patterns) {
      final category = pattern['category'] as String? ?? '未分類';
      grouped.putIfAbsent(category, () => []);
      grouped[category]!.add(pattern);
      
      // カテゴリ内で確信度でソート
      grouped[category]!.sort((a, b) =>
          (b['confidence'] as double).compareTo(a['confidence'] as double));
    }
    return grouped;
  }

  // カテゴリごとのアイコンを取得
  IconData _getCategoryIcon(String category) {
    switch (category.toLowerCase()) {
      case 'information_gathering':
        return Icons.search;
      case 'communication':
        return Icons.chat;
      case 'problem_solving':
        return Icons.psychology;
      case 'learning':
        return Icons.school;
      default:
        return Icons.person_outline;
    }
  }

  // カテゴリの表示名を取得
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

  // 確信度に応じた色を取得
  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) {
      return Colors.green;
    } else if (confidence >= 0.6) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: MediaQuery.of(context).size.width * 0.8,
        height: MediaQuery.of(context).size.height * 0.8,
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'ユーザーの傾向',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      tooltip: '傾向を再分析',
                      onPressed: () {
                        setState(() {
                          _loadPatterns();
                        });
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      tooltip: '閉じる',
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ],
            ),
            const Divider(),
            Expanded(
              child: FutureBuilder<List<Map<String, dynamic>>>(
                future: _patternsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  if (snapshot.hasError) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: Colors.red,
                            size: 48,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'エラーが発生しました：\n${snapshot.error}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.red),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: _loadPatterns,
                            child: const Text('再読み込み'),
                          ),
                        ],
                      ),
                    );
                  }

                  if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.analytics_outlined,
                            size: 48,
                            color: Colors.grey,
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            '分析された傾向はまだありません',
                            style: TextStyle(
                              fontSize: 16,
                              color: Colors.grey,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'チャット履歴から傾向を分析します',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey,
                            ),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: _loadPatterns,
                            icon: const Icon(Icons.refresh),
                            label: const Text('分析を実行'),
                          ),
                        ],
                      ),
                    );
                  }

                  // パターンをカテゴリごとにグループ化して確信度でソート
                  final patternsByCategory = _groupPatternsByCategory(snapshot.data!);
                  return Column(
                    children: [
                      Expanded(
                        child: ListView.builder(
                          itemCount: patternsByCategory.length,
                          itemBuilder: (context, index) {
                            final category = patternsByCategory.keys.elementAt(index);
                            final patterns = patternsByCategory[category]!;
                            
                            return ExpansionTile(
                              title: Row(
                                children: [
                                  Icon(_getCategoryIcon(category), size: 24),
                                  const SizedBox(width: 8),
                                  Text(
                                    _getCategoryDisplayName(category),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                ],
                              ),
                              initiallyExpanded: true,
                              children: patterns.map((pattern) {
                                return Card(
                                  margin: const EdgeInsets.symmetric(
                                    horizontal: 16,
                                    vertical: 4,
                                  ),
                                  child: ListTile(
                                    title: Text(
                                      pattern['pattern']?.replaceAll(RegExp(r'```markdown\n|```$'), '') ?? '',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        SizedBox(height: 4),
                                        Wrap(
                                          spacing: 4,
                                          runSpacing: 4,
                                          children: (pattern['suggested_labels'] as List<dynamic>? ?? [])
                                              .map<Widget>((label) => Container(
                                                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                    decoration: BoxDecoration(
                                                      color: Theme.of(context).colorScheme.primaryContainer,
                                                      borderRadius: BorderRadius.circular(12),
                                                    ),
                                                    child: Text(
                                                      label ?? '',
                                                      style: TextStyle(
                                                        fontSize: 12,
                                                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                                                      ),
                                                    ),
                                                  ))
                                              .toList(),
                                        ),
                                      ],
                                    ),
                                    trailing: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Container(
                                          width: 60,
                                          child: Column(
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              Text(
                                                '${(pattern['confidence'] * 100).toStringAsFixed(0)}%',
                                                style: TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                  color: _getConfidenceColor(pattern['confidence']),
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                        IconButton(
                                          icon: const Icon(Icons.info_outline),
                                          tooltip: '詳細を表示',
                                          onPressed: () {
                                            // TODO: 詳細表示ダイアログを表示
                                            showDialog(
                                              context: context,
                                              builder: (context) => AlertDialog(
                                                title: Text(pattern['pattern'] ?? ''),
                                                content: SingleChildScrollView(
                                                  child: Column(
                                                    mainAxisSize: MainAxisSize.min,
                                                    crossAxisAlignment: CrossAxisAlignment.start,
                                                    children: [
                                                      Text(
                                                        '関連する振り返り:',
                                                        style: Theme.of(context).textTheme.titleMedium,
                                                      ),
                                                      const SizedBox(height: 8),
                                                      ...pattern['examples'].map<Widget>((example) =>
                                                        Padding(
                                                          padding: const EdgeInsets.only(bottom: 8),
                                                          child: Card(
                                                            child: Padding(
                                                              padding: const EdgeInsets.all(8),
                                                              child: Text(example),
                                                            ),
                                                          ),
                                                        )
                                                      ).toList(),
                                                    ],
                                                  ),
                                                ),
                                                actions: [
                                                  TextButton(
                                                    onPressed: () => Navigator.of(context).pop(),
                                                    child: const Text('閉じる'),
                                                  ),
                                                ],
                                              ),
                                            );
                                          },
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }).toList(),
                            );
                          },
                        ),
                      ),
                      const Divider(),
                      Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              onPressed: () {
                                showDialog(
                                  context: context,
                                  builder: (context) => ReflectionBoardDialog(
                                    patterns: snapshot.data!,
                                  ),
                                );
                              },
                              icon: const Icon(Icons.dashboard),
                              label: const Text('Board形式で表示'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}