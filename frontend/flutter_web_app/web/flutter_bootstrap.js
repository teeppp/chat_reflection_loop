// flutter_bootstrap.js
// 環境設定をロードし、Flutterアプリケーションを初期化するスクリプト

async function initializeApp() {
    try {
        // ビルド時に注入された設定を使用
        if (!window.runtimeConfig) {
            throw new Error('ランタイム設定が見つかりません。アプリケーションを正しくビルドしてください。');
        }

        // グローバル設定オブジェクトを初期化
        window.flutterWebEnvironment = {
            apiKey: window.runtimeConfig.firebase.apiKey,
            authDomain: window.runtimeConfig.firebase.authDomain,
            projectId: window.runtimeConfig.firebase.projectId,
            storageBucket: window.runtimeConfig.firebase.storageBucket,
            messagingSenderId: window.runtimeConfig.firebase.messagingSenderId,
            appId: window.runtimeConfig.firebase.appId,
            measurementId: window.runtimeConfig.firebase.measurementId,
            apiBaseUrl: window.runtimeConfig.api.baseUrl
        };

        // デバッグモードの場合、設定をコンソールに出力
        if (window.location.hostname === 'localhost') {
            console.log('Flutter Web Environment:', {
                ...window.flutterWebEnvironment,
                apiKey: '[MASKED]'  // APIキーは表示しない
            });
        }

        // Flutterアプリケーションを初期化
        _flutter = {
            loader: {
                loadEntrypoint: function() {
                    return Promise.resolve();
                }
            }
        };

        // main.dart.jsを読み込む
        const script = document.createElement('script');
        script.src = 'main.dart.js';
        document.body.appendChild(script);

    } catch (error) {
        console.error('アプリケーションの初期化エラー:', error);
        // エラーメッセージをUIに表示
        document.body.innerHTML = `
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <h1>エラーが発生しました</h1>
                <p>アプリケーションの初期化中にエラーが発生しました。</p>
                <p>詳細はコンソールを確認してください。</p>
            </div>
        `;
    }
}

// ページロード時に初期化を実行
window.addEventListener('load', initializeApp);