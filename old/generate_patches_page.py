import json
import os
import datetime
import concurrent.futures

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("エラー: deep-translator がインストールされていません。")
    exit()

# 翻訳設定
translator = GoogleTranslator(source='en', target='ja')

# 3つのプロジェクトの情報
PROJECTS = {
    'revanced': {'name': '公式 ReVanced', 'file': 'revanced-dev-patches-list.json', 'color': '#888'},
    'morphe': {'name': '公式 MorpheApp', 'file': 'MorpheApp-patches-list.json', 'color': '#3ea6ff'},
    'anddea': {'name': 'anddea版 Morphe', 'file': 'andda-patches-list.json', 'color': '#ff4e4e'}
}

# YouTubeのパッケージ名
TARGET_PACKAGE = 'com.google.android.youtube'

def translate_text(text):
    if not text: return ""
    try: return translator.translate(text)
    except: return text

def get_yt_patches(filename):
    patches = {}
    if not os.path.exists(filename): return patches
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # --- ここが重要！ ---
            # 1. 辞書形式で、中に 'patches' というキーがある場合 (ReVanced公式に多い)
            if isinstance(data, dict) and 'patches' in data:
                patch_list = data['patches']
            # 2. リスト形式で、最初からパッチが並んでいる場合 (Morphe等に多い)
            elif isinstance(data, list):
                patch_list = data
            # 3. それ以外（辞書だけどpatchesキーがない）
            elif isinstance(data, dict):
                patch_list = list(data.values()) # 強引に中身をリスト化
            else:
                patch_list = []
            
            for p in patch_list:
                # 辞書型でない要素はスキップ
                if not isinstance(p, dict): continue
                
                name = p.get('name', 'Unknown')
                compat = p.get('compatiblePackages')
                
                # YouTube用かどうかの判定
                is_yt = False
                if compat is None: # 共通パッチ
                    is_yt = True
                elif isinstance(compat, list):
                    # リストの中に com.google.android.youtube があるか
                    for pkg in compat:
                        pkg_name = pkg.get('name') if isinstance(pkg, dict) else pkg
                        if pkg_name == TARGET_PACKAGE:
                            is_yt = True
                            break
                elif isinstance(compat, dict) and TARGET_PACKAGE in compat:
                    is_yt = True
                
                if is_yt:
                    patches[name] = p.get('description', '')
    except Exception as e:
        print(f"Error in {filename}: {e}")
    return patches

def process_patch_data(name, all_project_patches):
    # 翻訳
    name_ja = translate_text(name)
    
    # 説明文の取得（ReVanced > Morphe > anddeaの順で標準的なものを優先）
    desc_en = all_project_patches['revanced'].get(name) or all_project_patches['morphe'].get(name) or all_project_patches['anddea'].get(name) or ""
    desc_ja = translate_text(desc_en) if desc_en else ""
    
    # パッチ名を結合
    combined_name = f"{name} <span class='name-ja'>/ {name_ja}</span>" if name_ja and name_ja != name else name
    
    return {
        'id': name,
        'name_html': combined_name,
        'in_revanced': name in all_project_patches['revanced'],
        'in_morphe': name in all_project_patches['morphe'],
        'in_anddea': name in all_project_patches['anddea'],
        'desc_ja': desc_ja
    }

def generate_html(patch_rows, counts):
    now = datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    # HTMLの構築（文字列結合）
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube パッチ詳細比較・紹介ページ</title>
    <style>
        :root {{
            --bg-color: #0f0f0f;
            --card-bg: #1e1e1e;
            --text-color: #f1f1f1;
            --text-secondary: #aaaaaa;
            --yt-red: #ff0000;
            --border-color: #333333;
            --revanced-color: {PROJECTS['revanced']['color']};
            --morphe-color: {PROJECTS['morphe']['color']};
            --anddea-color: {PROJECTS['anddea']['color']};
        }}
        body {{
            font-family: "Roboto", "Arial", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid var(--yt-red);
            padding-bottom: 20px;
        }}
        h1 {{ margin: 0; font-size: 2.5em; }}
        .subtitle {{ color: var(--text-secondary); margin-top: 10px; }}

        /* サマリーセクション */
        .summary-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border-color);
            transition: transform 0.2s;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .card-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 15px; display: flex; align-items: center; }}
        .card-icon {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; }}
        .patch-count {{ font-size: 3em; font-weight: bold; color: var(--yt-red); line-height: 1; }}
        .total-patches .patch-count {{ color: var(--text-color); }}
        .card-desc {{ color: var(--text-secondary); font-size: 0.9em; margin-top: 10px; }}

        /* 推奨セクション */
        .recommend-section {{
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 40px;
            border: 1px solid var(--border-color);
        }}
        .recommend-section h2 {{ margin-top: 0; color: var(--yt-red); }}
        .recommend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .rec-item h3 {{ margin-bottom: 5px; }}
        .rec-item p {{ margin-top: 0; color: var(--text-secondary); font-size: 0.95em; }}

        /* 検索・テーブル */
        .search-container {{
            margin-bottom: 20px;
            position: sticky;
            top: 10px;
            z-index: 100;
        }}
        #search-input {{
            width: 100%;
            padding: 15px 20px;
            font-size: 1.1em;
            background-color: var(--card-bg);
            color: var(--text-color);
            border: 2px solid var(--border-color);
            border-radius: 30px;
            box-sizing: border-box;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        #search-input:focus {{ outline: none; border-color: var(--yt-red); }}

        .table-container {{
            background-color: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }}
        th, td {{
            text-align: left;
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background-color: rgba(255,255,255,0.05);
            font-weight: bold;
            position: sticky;
            top: 65px; /* 検索窓の下 */
            z-index: 90;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background-color: rgba(255,255,255,0.03); }}

        /* 列幅調整 */
        .col-name {{ width: 25%; }}
        .col-check {{ width: 10%; text-align: center; }}
        .col-desc {{ width: 45%; }}

        .name-ja {{ color: var(--text-secondary); font-size: 0.9em; font-weight: normal; }}
        .check-icon {{ font-size: 1.3em; font-weight: bold; }}
        .check-y {{ color: #2ecc71; }} /* 緑の〇 */
        .check-n {{ color: #e74c3c; opacity: 0.3; }} /* 赤の- */

        footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.9em;
        }}

        /* レスポンシブ対応 */
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8em; }}
            th, td {{ padding: 10px; font-size: 0.9em; }}
            .col-name {{ width: 35%; }}
            .col-desc {{ width: 45%; }}
            .check-icon {{ font-size: 1.1em; }}
            th {{ top: 60px; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1>YouTube パッチ詳細比較</h1>
        <div class="subtitle">快適なYouTube環境を構築するための、プロジェクト別機能一覧</div>
    </header>

    <section class="summary-section">
        <div class="card total-patches">
            <div class="card-title">総パッチ数 (Unique)</div>
            <div class="patch-count">{counts['total']}</div>
            <div class="card-desc">3つのプロジェクトで確認された、YouTube向け機能の合計</div>
        </div>
        <div class="card">
            <div class="card-title"><span class="card-icon" style="background-color:var(--revanced-color)"></span>{PROJECTS['revanced']['name']}</div>
            <div class="patch-count">{counts['revanced']}</div>
            <div class="card-desc">安定性と標準機能を重視した、公式のパッチセット</div>
        </div>
        <div class="card">
            <div class="card-title"><span class="card-icon" style="background-color:var(--morphe-color)"></span>{PROJECTS['morphe']['name']}</div>
            <div class="patch-count">{counts['morphe']}</div>
            <div class="card-desc">Material You対応やPlayストア更新無効化など、独自機能を持つ本家Morphe</div>
        </div>
        <div class="card">
            <div class="card-title"><span class="card-icon" style="background-color:var(--anddea-color)"></span>{PROJECTS['anddea']['name']}</div>
            <div class="patch-count">{counts['anddea']}</div>
            <div class="card-desc">AI要約(Gemini)や多言語翻訳(Yandex)など、最新・多機能を追求するanddea氏版</div>
        </div>
    </section>

    <section class="recommend-section">
        <h2>クイック・推奨ナビ</h2>
        <div class="recommend-grid">
            <div class="rec-item">
                <h3>🛡️ 安定・標準を求めるなら</h3>
                <p><strong>「公式 ReVanced」</strong>が最適です。最も多くのユーザーに使われており、バグが少なく、YouTubeのアップデートへの追従も安定しています。</p>
            </div>
            <div class="rec-item">
                <h3>🎨 デザインや独自設定を重視するなら</h3>
                <p><strong>「公式 MorpheApp」</strong>を検討してください。アプリの色を端末のテーマに合わせるMaterial Youや、勝手なアプリ更新を止めるパッチがあります。</p>
            </div>
            <div class="rec-item">
                <h3>🤖 AI機能や最新技術を試したいなら</h3>
                <p><strong>「anddea版 Morphe」</strong>一択です。動画のAI要約(Gemini)や、ロシア語等の動画を日本語吹き替えにする機能(Yandex)など、他にはない強力なパッチが揃っています。</p>
            </div>
        </div>
    </section>

    <section class="search-container">
        <input type="text" id="search-input" placeholder="パッチ名、機能、説明から検索... (例: AI, 広告, 翻訳)">
    </section>

    <section class="table-container">
        <table id="patches-table">
            <thead>
                <tr>
                    <th class="col-name">パッチ名 (EN / JA)</th>
                    <th class="col-check" style="color:var(--revanced-color)">ReVanced</th>
                    <th class="col-check" style="color:var(--morphe-color)">Morphe</th>
                    <th class="col-check" style="color:var(--anddea-color)">anddea</th>
                    <th class="col-desc">説明 (日本語)</th>
                </tr>
            </thead>
            <tbody>
"""

    # テーブル行の追加
    for row in patch_rows:
        rev_check = "<span class='check-icon check-y'>〇</span>" if row['in_revanced'] else "<span class='check-icon check-n'>-</span>"
        mor_check = "<span class='check-icon check-y'>〇</span>" if row['in_morphe'] else "<span class='check-icon check-n'>-</span>"
        and_check = "<span class='check-icon check-y'>〇</span>" if row['in_anddea'] else "<span class='check-icon check-n'>-</span>"
        
        html += f"""                <tr>
                    <td>{row['name_html']}</td>
                    <td class="col-check">{rev_check}</td>
                    <td class="col-check">{mor_check}</td>
                    <td class="col-check">{and_check}</td>
                    <td>{row['desc_ja']}</td>
                </tr>
"""

    # フッターとJSの構築
    html += f"""            </tbody>
        </table>
    </section>

    <footer>
        データソース: 各プロジェクト公開のJSONリスト ({now}時点)<br>
        このページは自動生成されました。
    </footer>
</div>

<script>
    // リアルタイム検索機能
    document.getElementById('search-input').addEventListener('keyup', function() {{
        const input = document.getElementById('search-input');
        const filter = input.value.toLowerCase();
        const table = document.getElementById('patches-table');
        const tr = table.getElementsByTagName('tr');

        // テーブルの行をループ（ヘッダーを除くのでi=1から）
        for (let i = 1; i < tr.length; i++) {{
            // 名前(0列目)と説明(4列目)を検索対象にする
            const nameCol = tr[i].getElementsByTagName('td')[0];
            const descCol = tr[i].getElementsByTagName('td')[4];
            
            if (nameCol || descCol) {{
                const nameText = nameCol.textContent || nameCol.innerText;
                const descText = descCol.textContent || descCol.innerText;
                
                // キーワードが含まれているか判定
                if (nameText.toLowerCase().indexOf(filter) > -1 || descText.toLowerCase().indexOf(filter) > -1) {{
                    tr[i].style.display = ""; // 表示
                }} else {{
                    tr[i].style.display = "none"; // 非表示
                }}
            }}
        }}
    }});
</script>

</body>
</html>
"""
    return html

def main():
    print("=== YouTube パッチ詳細比較 HTMLページ生成スクリプト ===")
    
    # 1. 各プロジェクトからYouTubeパッチを取得
    print("JSONファイルを解析中...")
    all_project_patches = {
        'revanced': get_yt_patches(PROJECTS['revanced']['file']),
        'morphe': get_yt_patches(PROJECTS['morphe']['file']),
        'anddea': get_yt_patches(PROJECTS['anddea']['file'])
    }
    
    # 2. 集計
    counts = {
        'revanced': len(all_project_patches['revanced']),
        'morphe': len(all_project_patches['morphe']),
        'anddea': len(all_project_patches['anddea'])
    }
    all_patch_names = sorted(list(set(all_project_patches['revanced'].keys()) | set(all_project_patches['morphe'].keys()) | set(all_project_patches['anddea'].keys())))
    counts['total'] = len(all_patch_names)
    
    print(f"解析完了: 合計 {counts['total']} 個のパッチが見つかりました。")
    print(f"(ReVanced: {counts['revanced']}, Morphe: {counts['morphe']}, anddea: {counts['anddea']})")
    print("説明文の翻訳とHTMLデータの構築を開始します (1〜2分かかります)...")
    
    # 3. マルチスレッドで翻訳と行データの作成
    patch_rows = []
    # 翻訳APIのブロックを避けるためスレッド数は5に制限
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_patch_data, name, all_project_patches): name for name in all_patch_names}
        
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            print(f"\r進捗: {count}/{counts['total']} 完了...", end="")
            patch_rows.append(future.result())

    print("\n翻訳完了。ABC順にソートしています...")
    patch_rows = sorted(patch_rows, key=lambda x: x['id'])
    
    # 4. HTML生成
    print("HTMLファイルを生成しています...")
    final_html = generate_html(patch_rows, counts)
    
    output_file = 'index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"\nすべての処理が完了しました！")
    print(f"出力ファイル: {output_file}")
    print("このファイルをブラウザで開いて確認してください。")

if __name__ == "__main__":
    main()