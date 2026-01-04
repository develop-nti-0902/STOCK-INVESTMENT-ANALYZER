/**
 * バッチ実行管理画面のJavaScript
 * バッチの実行と履歴表示を管理
 */

// DOM要素の取得
const batchTypeSelect = document.getElementById('batch-type');
const batchSizeSelect = document.getElementById('batch-size');
const batchSizeGroup = document.getElementById('batch-size-group');
const timeframeSelect = document.getElementById('timeframe');
const timeframeGroup = document.getElementById('timeframe-group');
const listBatchSizeInput = document.getElementById('list-batch-size');
const listBatchSizeGroup = document.getElementById('list-batch-size-group');
const sampleSizeInput = document.getElementById('sample-size');
const sampleSizeGroup = document.getElementById('sample-size-group');
const executeBatchBtn = document.getElementById('execute-batch-btn');
const refreshHistoryBtn = document.getElementById('refresh-history-btn');
const historyTbody = document.getElementById('history-tbody');
const statusMessage = document.getElementById('status-message');

// API エンドポイント（環境に応じて変更可能）
const API_BASE_URL = '/api/v1';

/**
 * ステータスメッセージを表示
 * @param {string} message - 表示するメッセージ
 * @param {string} type - メッセージタイプ (success, error, info, warning)
 */
function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');

    // 5秒後に自動的に非表示
    setTimeout(() => {
        statusMessage.classList.add('hidden');
    }, 5000);
}

/**
 * ステータスバッジのHTMLを生成
 * @param {string} status - バッチステータス
 * @returns {string} バッジのHTML
 */
function createStatusBadge(status) {
    const statusLower = status.toLowerCase();
    let badgeClass = 'pending';
    let displayText = status;

    if (statusLower === 'completed' || statusLower === 'success') {
        badgeClass = 'completed';
        displayText = '完了';
    } else if (statusLower === 'failed' || statusLower === 'error') {
        badgeClass = 'failed';
        displayText = '失敗';
    } else if (statusLower === 'running') {
        badgeClass = 'running';
        displayText = '実行中';
    } else if (statusLower === 'pending') {
        badgeClass = 'pending';
        displayText = '待機中';
    }

    return `<span class="status-badge ${badgeClass}">${displayText}</span>`;
}

/**
 * 処理時間を計算して表示
 * @param {string} startTime - 開始時刻
 * @param {string} endTime - 終了時刻
 * @returns {string} 処理時間の表示文字列
 */
function calculateDuration(startTime, endTime) {
    if (!startTime || !endTime) return '-';

    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end - start;

    if (diffMs < 0) return '-';

    const diffSec = Math.floor(diffMs / 1000);
    const minutes = Math.floor(diffSec / 60);
    const seconds = diffSec % 60;

    if (minutes > 0) {
        return `${minutes}分${seconds}秒`;
    }
    return `${seconds}秒`;
}

/**
 * 日時を日本語フォーマットで表示
 * @param {string} dateTimeStr - ISO形式の日時文字列
 * @returns {string} フォーマット済み日時文字列
 */
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '-';

    const date = new Date(dateTimeStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * バッチを実行
 */
async function executeBatch() {
    const batchType = batchTypeSelect.value;
    const timeframe = timeframeSelect ? timeframeSelect.value : '';

    // 実行前の確認(resetの場合)
    if (batchType === 'reset') {
        if (!confirm('⚠️ 警告: 全ての銘柄マスタデータが削除されます。\n本当に実行しますか?')) {
            return;
        }
    }

    // ボタンを無効化
    executeBatchBtn.disabled = true;
    executeBatchBtn.innerHTML = '<span class="loading"></span> 実行中...';

    try {
        let url;
        let method = 'POST';

        if (batchType === 'jpx_all') {
            // JPX 全銘柄取得 API
            url = `${API_BASE_URL}/batch/stock-data/jpx-all`;
            method = 'POST';
        } else if (batchType === 'jpx_all_multi') {
            // JPX 全銘柄取得（マルチ）API
            url = `${API_BASE_URL}/batch/stock-data/jpx-all/multi`;
            method = 'POST';
        } else {
            // stock-master 用 API (refresh / reset)
            url = `${API_BASE_URL}/stock-master/${batchType}`;
            method = batchType === 'reset' ? 'DELETE' : 'POST';

            // refreshの場合にbatch_sizeをクエリパラメータとして追加
            if (batchType === 'refresh') {
                const batchSize = batchSizeSelect.value;
                url += `?batch_size=${batchSize}`;
            }
        }

        // refresh_sample の場合は専用エンドポイントに sample_size と batch_size をクエリで渡す
        if (batchType === 'refresh_sample') {
            const batchSize = batchSizeSelect.value;
            const sampleSize = sampleSizeInput ? parseInt(sampleSizeInput.value, 10) : 100;
            url = `${API_BASE_URL}/stock-master/refresh/sample?sample_size=${sampleSize}&batch_size=${batchSize}`;
            method = 'POST';
        }

        // fetch オプションを組み立て（jpx_all は JSON ボディを送信）
        const fetchOptions = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (batchType === 'jpx_all') {
            const payload = { timeframe: timeframe };
            fetchOptions.body = JSON.stringify(payload);
        } else if (batchType === 'jpx_all_multi') {
            const listBatchSize = listBatchSizeInput ? parseInt(listBatchSizeInput.value, 10) : 50;
            const payload = { timeframe: timeframe, list_batch_size: listBatchSize };
            fetchOptions.body = JSON.stringify(payload);
        }

        const response = await fetch(url, fetchOptions);

        const result = await response.json();

        if (response.ok) {
            const count = result.updated_count || result.deleted_count || 0;
            const action = batchType === 'refresh' ? '更新' : '削除';
            showStatus(`${result.message || 'バッチ実行完了'} (${action}件数: ${count})`, 'success');
        } else {
            showStatus(`エラー: ${result.detail || result.message || '不明なエラー'}`, 'error');
        }
    } catch (error) {
        console.error('バッチ実行エラー:', error);
        showStatus(`バッチ実行に失敗しました: ${error.message}`, 'error');
    } finally {
        // ボタンを有効化
        executeBatchBtn.disabled = false;
        executeBatchBtn.innerHTML = '<span class="btn-icon">▶</span> バッチ実行';
    }
}

/**
 * バッチ実行履歴を取得して表示
 *
 * NOTE: 現在は履歴取得APIが未実装のため、ダミーメッセージを表示
 */
async function loadBatchHistory() {
    try {
        // TODO: バッチ履歴APIが実装されたら有効化
        // const response = await fetch(`${API_BASE_URL}/batch/history?limit=20`);

        // テーブルをクリア
        historyTbody.innerHTML = '';

        // 一旦、履歴機能は未実装メッセージを表示
        historyTbody.innerHTML = '<tr><td colspan="7" class="no-data">履歴機能は開発中です</td></tr>';

        /* 将来の実装用コード
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        const history = data.history || data.items || data || [];

        if (history.length === 0) {
            historyTbody.innerHTML = '<tr><td colspan="7" class="no-data">実行履歴がありません</td></tr>';
            return;
        }

        // 履歴データを行として追加
        history.forEach(item => {
            const row = document.createElement('tr');

            const id = item.id || item.execution_id || '-';
            const batchType = item.batch_type || item.batch_name || '-';
            const status = item.status || 'unknown';
            const startTime = formatDateTime(item.start_time || item.started_at);
            const endTime = formatDateTime(item.end_time || item.ended_at);
            const duration = calculateDuration(item.start_time || item.started_at, item.end_time || item.ended_at);
            const message = item.message || item.error_message || '-';

            row.innerHTML = `
                <td>${id}</td>
                <td>${batchType}</td>
                <td>${createStatusBadge(status)}</td>
                <td>${startTime}</td>
                <td>${endTime}</td>
                <td>${duration}</td>
                <td>${message}</td>
            `;

            historyTbody.appendChild(row);
        });
        */
    } catch (error) {
        console.error('履歴取得エラー:', error);
        historyTbody.innerHTML = `<tr><td colspan="7" class="no-data">履歴機能は開発中です</td></tr>`;
    }
}

/**
 * バッチ種別変更時の処理
 */
function onBatchTypeChange() {
    const batchType = batchTypeSelect.value;

    // refreshの場合はbatch_sizeを表示、refresh_sampleはbatch_sizeとsample_sizeを表示
    if (batchType === 'refresh') {
        batchSizeGroup.style.display = 'flex';
        if (sampleSizeGroup) sampleSizeGroup.style.display = 'none';
        if (timeframeGroup) timeframeGroup.style.display = 'none';
        if (listBatchSizeGroup) listBatchSizeGroup.style.display = 'none';
    } else if (batchType === 'refresh_sample') {
        batchSizeGroup.style.display = 'flex';
        if (sampleSizeGroup) sampleSizeGroup.style.display = 'flex';
        if (timeframeGroup) timeframeGroup.style.display = 'none';
        if (listBatchSizeGroup) listBatchSizeGroup.style.display = 'none';
    } else if (batchType === 'jpx_all') {
        batchSizeGroup.style.display = 'none';
        if (sampleSizeGroup) sampleSizeGroup.style.display = 'none';
        if (timeframeGroup) timeframeGroup.style.display = 'flex';
        if (listBatchSizeGroup) listBatchSizeGroup.style.display = 'none';
    } else if (batchType === 'jpx_all_multi') {
        batchSizeGroup.style.display = 'none';
        if (sampleSizeGroup) sampleSizeGroup.style.display = 'none';
        if (timeframeGroup) timeframeGroup.style.display = 'flex';
        if (listBatchSizeGroup) listBatchSizeGroup.style.display = 'flex';
    } else {
        batchSizeGroup.style.display = 'none';
        if (sampleSizeGroup) sampleSizeGroup.style.display = 'none';
        if (timeframeGroup) timeframeGroup.style.display = 'none';
        if (listBatchSizeGroup) listBatchSizeGroup.style.display = 'none';
    }
}

/**
 * 初期化処理
 */
function initialize() {
    // イベントリスナーの登録
    executeBatchBtn.addEventListener('click', executeBatch);
    refreshHistoryBtn.addEventListener('click', () => {
        showStatus('履歴を更新しています...', 'info');
        loadBatchHistory();
    });
    batchTypeSelect.addEventListener('change', onBatchTypeChange);

    // 初回の履歴読み込み
    loadBatchHistory();

    // 初期状態の設定
    onBatchTypeChange();
}

// DOMの読み込み完了後に初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
