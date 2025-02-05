import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/reflection_service.dart';
import './user_patterns_dialog.dart';

class ReflectionPreviewDialog extends StatefulWidget {
  final String threadId;
  final ReflectionService reflectionService;

  const ReflectionPreviewDialog({
    super.key,
    required this.threadId,
    required this.reflectionService,
  });

  @override
  State<ReflectionPreviewDialog> createState() => _ReflectionPreviewDialogState();
}

class _ReflectionPreviewDialogState extends State<ReflectionPreviewDialog> {
  late Future<String> _memoFuture;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadMemo();
  }

  Future<void> _loadMemo() async {
    if (mounted) {
      setState(() => _isLoading = true);
    }

    try {
      _memoFuture = widget.reflectionService.getReflectionMemo(widget.threadId);
      await _memoFuture;
    } catch (e) {
      print('振り返りメモの取得に失敗: $e');
      // 取得失敗時は振り返り更新を試みる
      try {
        await widget.reflectionService.updateReflection(
          threadId: widget.threadId,
          messageContent: '',  // 空文字で更新を要求
          isUserMessage: false,
        );
        // 更新後に再度取得を試みる
        if (mounted) {
          setState(() {
            _memoFuture = widget.reflectionService.getReflectionMemo(widget.threadId);
          });
        }
      } catch (updateError) {
        print('振り返りの更新に失敗: $updateError');
        if (mounted) {
          setState(() {
            _memoFuture = Future.error('振り返りメモの生成に失敗しました');
          });
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return Dialog(
      child: Container(
        width: size.width * 0.8,
        height: size.height * 0.8,
        padding: const EdgeInsets.all(16.0),
        constraints: BoxConstraints(
          minWidth: 300,
          maxWidth: size.width * 0.9,
          minHeight: 200,
          maxHeight: size.height * 0.9,
        ),
        child: Column(
          children: [
            SizedBox(
              width: double.infinity,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: const Text(
                      '振り返りメモ',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.psychology),
                        tooltip: 'ユーザーの傾向',
                        onPressed: () {
                          // 現在のダイアログを閉じて傾向ダイアログを表示
                          Navigator.of(context).pop();
                          showDialog(
                            context: context,
                            builder: (context) => UserPatternsDialog(
                              reflectionService: widget.reflectionService,
                            ),
                          );
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
            ),
            const Divider(),
            Expanded(
              child: FutureBuilder<String>(
                future: _memoFuture,
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
                            onPressed: _loadMemo,
                            child: const Text('再読み込み'),
                          ),
                        ],
                      ),
                    );
                  }

                  if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return const Center(
                      child: Text('振り返りメモはまだありません'),
                    );
                  }

                  return LayoutBuilder(
                    builder: (context, constraints) {
                      return SingleChildScrollView(
                        child: Container(
                          constraints: BoxConstraints(
                            minHeight: 100,
                            maxHeight: constraints.maxHeight,
                            maxWidth: constraints.maxWidth,
                          ),
                          child: Markdown(
                            data: snapshot.data!,
                            selectable: true,
                            shrinkWrap: true,
                            padding: EdgeInsets.zero,
                          ),
                        ),
                      );
                    },
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