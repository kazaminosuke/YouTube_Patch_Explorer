import json
import os
import requests
import pandas as pd
import time

# --- 設定 ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "translategemma:12b"  # 最高精度の12Bモデル

def translate_with_gemma(text, is_name=False):
    if not text or text == "-" or len(text) < 2:
        return text
    
    # 12Bモデルが最も「翻訳モード」に入りやすいプロンプト形式
    prompt = f"English: {text}\nJapanese:"

    # VRAM溢れによるタイムアウトを防ぐため長めに設定
    for attempt in range(3):
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2, # 創造性を抑えて正確に
                    "num_predict": 256,
                    "top_p": 0.9
                }
            }, timeout=120)
            
            result = response.json().get("response", "").strip()
            # 翻訳結果の後に余計な解説が入った場合は最初の1行目だけ取る
            translated = result.split('\n')[0].replace("Japanese:", "").strip()
            return translated
        except Exception as e:
            if attempt < 2:
                print(f"\n[Retry] 再試行中... ({attempt+1}/3)")
                time.sleep(2)
            else:
                print(f"\n[Error] 翻訳失敗: {text[:20]}...")
                return text

def get_patches(filename, target_type):
    patches = {}
    if not os.path.exists(filename): return patches
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
                    if compat is None or (isinstance(compat, (dict, list)) and len(compat) == 0): is_target = True
                elif target_type == 'youtube':
                    target = 'com.google.android.youtube'
                    if isinstance(compat, dict) and target in compat: is_target = True
                    elif isinstance(compat, list) and any((pkg.get('name') if isinstance(pkg, dict) else pkg) == target for pkg in compat): is_target = True
                elif target_type == 'ytmusic':
                    target = 'com.google.android.apps.youtube.music'
                    if isinstance(compat, dict) and target in compat: is_target = True
                    elif isinstance(compat, list) and any((pkg.get('name') if isinstance(pkg, dict) else pkg) == target for pkg in compat): is_target = True
                
                if is_target: patches[name] = desc
    except: pass
    return patches

def get_sheet_data(category_name, target_type, files):
    print(f"\n--- 【{category_name}】解析開始 (Model: {MODEL_NAME}) ---")
    rev_p = get_patches(files[0], target_type)
    mor_p = get_patches(files[1], target_type)
    and_p = get_patches(files[2], target_type)
    
    all_names = sorted(list(set(rev_p.keys()) | set(mor_p.keys()) | set(and_p.keys())))
    if not all_names: return None, None

    print(f"合計 {len(all_names)} 件を順次翻訳します。GPU負荷に注意してください。")
    
    table_data = []
    for i, name in enumerate(all_names, 1):
        # パッチ名と説明を個別に翻訳（12Bの性能をフルに使う）
        name_ja = translate_with_gemma(name, is_name=True)
        desc_en = rev_p.get(name) or mor_p.get(name) or and_p.get(name) or ""
        desc_ja = translate_with_gemma(desc_en)
        
        combined_name = f"{name} / {name_ja}"
        row = [
            combined_name,
            "〇" if name in rev_p else "-",
            "〇" if name in mor_p else "-",
            "〇" if name in and_p else "-",
            desc_ja
        ]
        table_data.append(row)
        print(f"\r進捗: {i}/{len(all_names)} 完了 {'#' * (i * 20 // len(all_names))}", end="", flush=True)

    print("\nシート完了。")
    header = ["パッチ名 (EN / JA)", f"ReVanced ({len(rev_p)})", f"Morphe ({len(mor_p)})", f"anddea ({len(and_p)})", "説明 (JA)"]
    return table_data, header

def main():
    # JSONファイル名が正しいか確認
    files = ['revanced-dev-patches-list.json', 'MorpheApp-patches-list.json', 'andda-patches-list.json']
    output_file = 'Patch_Comparison_12B_Quality.xlsx'

    # 各カテゴリを順番に実行
    yt_data, yt_head = get_sheet_data("YouTube", "youtube", files)
    ytm_data, ytm_head = get_sheet_data("YT Music", "ytmusic", files)
    univ_data, univ_head = get_sheet_data("Universal", "universal", files)

    print(f"\nExcel保存中: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if yt_data: pd.DataFrame(yt_data, columns=yt_head).to_excel(writer, sheet_name='YouTube', index=False)
        if ytm_data: pd.DataFrame(ytm_data, columns=ytm_head).to_excel(writer, sheet_name='YT Music', index=False)
        if univ_data: pd.DataFrame(univ_data, columns=univ_head).to_excel(writer, sheet_name='Universal', index=False)

    print("✨ すべての翻訳が完了しました！プロ級の比較表をお楽しみください。")

if __name__ == "__main__":
    main()