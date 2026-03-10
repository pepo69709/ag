// ===============================================
// 🚀 AI-TRAINER：全自動・絶対遅刻しないタイマー (GAS用)
// ===============================================

const GITHUB_USERNAME = "upupup109"; // あなたのGitHub名
const REPOSITORY_NAME = "stock-backtester"; // リポジトリ名
const WORKFLOW_FILE_NAME = "daily_scan.yml"; // 動かしたいファイル

function triggerGitHubAction() {
    // --- 🛑 追加：土日と夜間はストップするフィルター ---
    const now = new Date();
    const jstNow = new Date(now.getTime() + 9 * 60 * 60 * 1000); // 日本時間に変換
    const day = jstNow.getUTCDay(); // 0(日)〜6(土)
    const hour = jstNow.getUTCHours(); // 0〜23

    // 土日は動かさない
    if (day === 0 || day === 6) {
        Logger.log("💤 今日は休場日（土日）なのでスキップします。");
        return;
    }
    // 日本時間の 9時〜15時の間「以外」は動かさない
    if (hour < 9 || hour > 15) {
        Logger.log("🌙 現在は取引時間外なのでスキップします。");
        return;
    }
    // ----------------------------------------

    const p = PropertiesService.getScriptProperties();
    const githubToken = p.getProperty("GITHUB_TOKEN");

    if (!githubToken) {
        Logger.log("エラー: GITHUB_TOKEN が設定されていません。");
        return;
    }
    const url = `https://api.github.com/repos/${GITHUB_USERNAME}/${REPOSITORY_NAME}/actions/workflows/${WORKFLOW_FILE_NAME}/dispatches`;
    const options = {
        method: "post",
        headers: {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": "Bearer " + githubToken
        },
        payload: JSON.stringify({ ref: "main" })
    };
    UrlFetchApp.fetch(url, options);
    Logger.log("✨ 成功: GitHub に強制実行の信号を送りました！");
}
