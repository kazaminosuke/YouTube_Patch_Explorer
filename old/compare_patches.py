import json
import os
import concurrent.futures

try:
    from deep_translator import GoogleTranslator
    import pandas as pd
except ImportError:
    print("エラー: 必要なライブラリがインストールされていません。")
    print("コマンドプロンプトで以下を実行してください:")
    print("pip install deep-translator pandas openpyxl")
    exit()

translator = GoogleTranslator(source='en', target='ja')

def translate_text(text):
    if not text:
        return ""
    try:
        return translator.translate(text)
    except Exception as e:
        return text 

def get_patches(filename, target_type):
    patches = {}
    if not os.path.exists(filename):
        return patches

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            patch_list = data.get('patches', data) if isinstance(data, dict) else data if isinstance(data, list) else []
                
            for p in patch_list:
                name = p.get('name', 'Unknown')
                desc = p.get('description', '') or ""
                desc = desc.replace("\n", " ").replace("\r", "")

                compat = p.get('compatiblePackages')
                is_target = False
                
                if target_type == 'universal':
                    if compat is None or (isinstance(compat, dict) and len(compat) == 0) or (isinstance(compat, list) and len(compat) == 0):
                        is_target = True
                elif target_type == 'youtube':
                    if isinstance(compat, dict) and 'com.google.android.youtube' in compat:
                        is_target = True
                    elif isinstance(compat, list) and any(pkg.get('name') == 'com.google.android.youtube' if isinstance(pkg, dict) else pkg == 'com.google.android.youtube' for pkg in compat):
                        is_target = True
                elif target_type == 'ytmusic':
                    if isinstance(compat, dict) and 'com.google.android.apps.youtube.music' in compat:
                        is_target = True
                    elif isinstance(compat, list) and any(pkg.get('name') == 'com.google.android.apps.youtube.music' if isinstance(pkg, dict) else pkg == 'com.google.android.apps.youtube.music' for pkg in compat):
                        is_target = True
                
                if is_target:
                    patches[name] = desc
    except Exception as e:
        pass
        
    return patches

def process_patch(name, revanced_patches, morphe_patches, anddea_patches):
    name_ja = translate_text(name)
    desc_en = revanced_patches.get(name) or morphe_patches.get(name) or anddea_patches.get(name) or ""
    desc_ja = translate_text(desc_en) if desc_en else ""
    
    combined_name = f"{name} / {name_ja}" if name_ja and name_ja != name else name
    
    return [
        combined_name,
        "〇" if name in revanced_patches else "-",
        "〇" if name in morphe_patches else "-",
        "〇" if name in anddea_patches else "-",
        desc_ja
    ]

def get_sheet_data(category_name, target_type, revanced_file, morphe_file, anddea_file):
    print(f"\n========== 【{category_name}】のデータを解析・翻訳中 ==========")
    
    revanced_patches = get_patches(revanced_file, target_type)
    morphe_patches = get_patches(morphe_file, target_type)
    anddea_patches = get_patches(anddea_file, target_type)

    all_patch_names = sorted(list(set(revanced_patches.keys()) | set(morphe_patches.keys()) | set(anddea_patches.keys())))
    
    if not all_patch_names:
        print(f"※ {category_name} 向けのパッチは見つかりませんでした。")
        return None, None

    print(f"合計 {len(all_patch_names)} 個のパッチを処理します...")
    
    table_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_patch, name, revanced_patches, morphe_patches, anddea_patches) for name in all_patch_names]
        
        count = 0
        total = len(all_patch_names)
        for future in concurrent.futures.as_completed(futures):
            count += 1
            print(f"\r進捗: {count}/{total} 完了...", end="")
            table_data.append(future.result())

    print() 
    table_data = sorted(table_data, key=lambda x: x[0])

    # ヘッダーにパッチ数を埋め込む
    header = [
        "パッチ名 (English / 日本語)",
        f"ReVanced ({len(revanced_patches)}個)",
        f"MorpheApp ({len(morphe_patches)}個)",
        f"anddea ({len(anddea_patches)}個)",
        "説明 (日本語)"
    ]
    
    return table_data, header

def main():
    revanced_file = 'revanced-dev-patches-list.json'
    morphe_file = 'MorpheApp-patches-list.json'
    anddea_file = 'andda-patches-list.json'

    # 各シート用のデータを取得
    yt_data, yt_header = get_sheet_data("YouTube", "youtube", revanced_file, morphe_file, anddea_file)
    ytm_data, ytm_header = get_sheet_data("YT Music", "ytmusic", revanced_file, morphe_file, anddea_file)
    univ_data, univ_header = get_sheet_data("Universal", "universal", revanced_file, morphe_file, anddea_file)

    output_file = 'Patch_Comparison_All.xlsx'
    print(f"\nExcelファイル ({output_file}) を作成しています...")

    # Pandasを使って1つのExcelファイルに複数シートを書き込む
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if yt_data:
            df_yt = pd.DataFrame(yt_data, columns=yt_header)
            df_yt.to_excel(writer, sheet_name='YouTube', index=False)
            
        if ytm_data:
            df_ytm = pd.DataFrame(ytm_data, columns=ytm_header)
            df_ytm.to_excel(writer, sheet_name='YT Music', index=False)
            
        if univ_data:
            df_univ = pd.DataFrame(univ_data, columns=univ_header)
            df_univ.to_excel(writer, sheet_name='Universal', index=False)

    print(f"完了！ 出力ファイル: {output_file}")

if __name__ == "__main__":
    main()