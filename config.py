# ==========================================
# ⚙️ YouTube Patch Explorer 設定ファイル
# ==========================================

# --- 基本設定 ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "translategemma:12b"
EXCEL_FILE = 'Patch_Comparison_All.xlsx'

# --- 取得元URL (Rawデータ) ---
PATCH_URLS = {
    'revanced-dev-patches-list.json': 'https://raw.githubusercontent.com/Jman-Github/ReVanced-Patch-Bundles/refs/heads/bundles/patch-bundles/revanced-patch-bundles/revanced-dev-patches-list.json', 
    'MorpheApp-patches-list.json': 'https://raw.githubusercontent.com/MorpheApp/morphe-patches/refs/heads/dev/patches-list.json', 
    'andda-patches-list.json': 'https://raw.githubusercontent.com/anddea/revanced-patches/refs/heads/dev/patches-list.json' 
}

# --- 翻訳スキップ（ホワイトリスト） ---
WHITELIST = [
    "change installer package name",
    "alternative thumbnails",
    "add more double tap to seek length options",
]

# --- パッチ名の統一（エイリアス） ---
ALIAS_MAP = {
    "hook download actions": "downloads",
}

# --- カスタム注釈（統合メッセージなど） ---
CUSTOM_MARKS = {
    "video ads": {"anddea": "〇 ※Hide adsに統合"},
    "video quality": {"anddea": "〇 ※Video playbackに統合"},
    "playback speed": {"anddea": "〇 ※Video playbackに統合"},
    "hide shorts components": {"anddea": "〇 ※Shorts componentsに統合"}
}