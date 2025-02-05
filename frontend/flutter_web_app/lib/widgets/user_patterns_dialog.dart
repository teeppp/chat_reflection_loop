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
  late Future<Map<String, dynamic>> _patternsFuture;

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

  // パターンビューを構築
  Widget _buildPatternsView(List<Map<String, dynamic>> patterns) {
    if (patterns.isEmpty) {
      return const Center(
        child: Text('パターンはまだ分析されていません'),
      );
    }

    return ListView.builder(
      itemCount: patterns.length,
      itemBuilder: (context, index) {
        final pattern = patterns[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: ListTile(
            title: Text(
              pattern['pattern'] ?? '',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Text(
              'カテゴリ: ${pattern['category'] ?? '未分類'}\n'
              '検出時刻: ${pattern['detected_at'] ?? '不明'}',
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '${((pattern['confidence'] as num? ?? 0) * 100).toStringAsFixed(0)}%',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: _getConfidenceColor(pattern['confidence'] ?? 0),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ラベルビューを構築
  Widget _buildLabelsView(List<Map<String, dynamic>> labels) {
    if (labels.isEmpty) {
      return const Center(
        child: Text('ラベルはまだ分析されていません'),
      );
    }

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: labels.map((label) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            label['text'] ?? '',
            style: TextStyle(
              color: Theme.of(context).colorScheme.onPrimaryContainer,
            ),
          ),
        );
      }).toList(),
    );
  }

  // クラスタービューを構築
  Widget _buildClustersView(List<Map<String, dynamic>> clusters) {
    if (clusters.isEmpty) {
      return const Center(
        child: Text('クラスターはまだ分析されていません'),
      );
    }

    return ListView.builder(
      itemCount: clusters.length,
      itemBuilder: (context, index) {
        final cluster = clusters[index];
        return ExpansionTile(
          title: Text(cluster['theme'] ?? 'クラスター ${index + 1}'),
          subtitle: Text('強度: ${((cluster['strength'] as num? ?? 0) * 100).toStringAsFixed(0)}%'),
          children: [
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: (cluster['labels'] as List? ?? []).map<Widget>((label) {
                  return Chip(
                    label: Text(label.toString()),
                    backgroundColor: Theme.of(context).colorScheme.secondaryContainer,
                    labelStyle: TextStyle(
                      color: Theme.of(context).colorScheme.onSecondaryContainer,
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        );
      },
    );
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
              child: FutureBuilder<Map<String, dynamic>>(
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
                          const Icon(Icons.error_outline, color: Colors.red, size: 48),
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

                  if (!snapshot.hasData ||
                      (snapshot.data!['patterns'] as List).isEmpty &&
                      (snapshot.data!['labels'] as List).isEmpty) {
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
                  final data = snapshot.data!;
                  final patterns = (data['patterns'] as List).cast<Map<String, dynamic>>();
                  final labels = (data['labels'] as List).cast<Map<String, dynamic>>();
                  final clusters = (data['clusters'] as List).cast<Map<String, dynamic>>();

                  return DefaultTabController(
                    length: 3,
                    child: Column(
                      children: [
                        Material(
                          color: Theme.of(context).colorScheme.surface,
                          child: TabBar(
                            labelColor: Theme.of(context).colorScheme.primary,
                            unselectedLabelColor: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                            indicatorColor: Theme.of(context).colorScheme.primary,
                            tabs: [
                              Tab(text: 'ラベル (${labels.length})'),
                              Tab(text: 'クラスター (${clusters.length})'),
                              Tab(text: 'パターン (${patterns.length})'),
                            ],
                          ),
                        ),
                        Expanded(
                          child: TabBarView(
                            children: [
                              // ラベルビュー
                              _buildLabelsView(labels),
                              
                              // クラスタービュー
                              _buildClustersView(clusters),
                              
                              // パターンビュー
                              _buildPatternsView(patterns),
                            ],
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
                                      patterns: patterns,
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
                    ),
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