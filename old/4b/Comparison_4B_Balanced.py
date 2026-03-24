import json
import os
import requests
import pandas as pd
import concurrent.futures
import time

# --- 設定 ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "translategemma:4b"  # 使用する4bモデルのタグ名に合わせて変更してください

def translate_with_gemma(text, is_name=False):
    if not text or text == "-" or len(text) < 2:
        return text
    
    # 厳格なFew-Shotプロンプト（挨拶や英語の解説を絶対に出力させない）
    prompt = f"""You are a professional translator. Translate the English text to Japanese. 
Output ONLY the translated Japanese text. Do not add any greetings, explanations, alternative options, or English words.

English: Hide shorts components
Japanese: ショート動画のコンポーネントを非表示にする

English: {text}
Japanese:"""

    for attempt in range(3):
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # 遊びをなくして正確に出力させる
                    "num_predict": 256,
                    "top_p": 0.9
                }
            }, timeout=45) 
            
            result = response.json().get("response", "").strip()
            
            # AIが余計な文字を付けた場合のクリーニング
            translated = result.split('\n')[0].replace("Japanese:", "").replace("English:", "").strip()
            if translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1]
                
            return translated
        except Exception as e:
            if attempt < 2:
                time.sleep(1.5)
            else:
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

def process_patch(name, rev_p, mor_p, and_p):
    name_ja = translate_with_gemma(name, is_name=True)
    desc_en = rev_p.get(name) or mor_p.get(name) or and_p.get(name) or ""
    desc_ja = translate_with_gemma(desc_en)
    
    combined_name = f"{name} / {name_ja}" if name_ja and name_ja != name else name
    return [
        combined_name,
        "〇" if name in rev_p else "-",
        "〇" if name in mor_p else "-",
        "〇" if name in and_p else "-",
        desc_ja
    ]

def get_sheet_data(category_name, target_type, files):
    print(f"\n--- 【{category_name}】解析開始 (Model: {MODEL_NAME}) ---")
    rev_p = get_patches(files[0], target_type)
    mor_p = get_patches(files[1], target_type)
    and_p = get_patches(files[2], target_type)
    
    all_names = sorted(list(set(rev_p.keys()) | set(mor_p.keys()) | set(and_p.keys())))
    if not all_names: return None, None

    print(f"合計 {len(all_names)} 件を翻訳します...")
    
    table_data = []
    # 4bクラスならVRAMに収まるので、安全に3並列で回す
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_patch, n, rev_p, mor_p, and_p) for n in all_names]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            print(f"\r進捗: {i}/{len(all_names)} 完了", end="", flush=True)
            table_data.append(future.result())

    print("\nシート完了。")
    # ソートし直す
    table_data = sorted(table_data, key=lambda x: x[0])
    
    header = ["パッチ名 (EN / JA)", f"ReVanced ({len(rev_p)})", f"Morphe ({len(mor_p)})", f"anddea ({len(and_p)})", "説明 (JA)"]
    return table_data, header

def main():
    files = ['revanced-dev-patches-list.json', 'MorpheApp-patches-list.json', 'andda-patches-list.json']
    output_file = 'Patch_Comparison_4B_Balanced.xlsx'

    yt_data, yt_head = get_sheet_data("YouTube", "youtube", files)
    ytm_data, ytm_head = get_sheet_data("YT Music", "ytmusic", files)
    univ_data, univ_head = get_sheet_data("Universal", "universal", files)

    print(f"\nExcel保存中: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if yt_data: pd.DataFrame(yt_data, columns=yt_head).to_excel(writer, sheet_name='YouTube', index=False)
        if ytm_data: pd.DataFrame(ytm_data, columns=ytm_head).to_excel(writer, sheet_name='YT Music', index=False)
        if univ_data: pd.DataFrame(univ_data, columns=univ_head).to_excel(writer, sheet_name='Universal', index=False)

    print("✨ すべての翻訳が完了しました！")

if __name__ == "__main__":
    main()