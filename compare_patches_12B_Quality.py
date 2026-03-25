import json
import os
import requests
import pandas as pd
import time
from config import * # 👈 新しく作ったconfig.pyから設定を全部読み込む！

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Gemini APIのセットアップ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI = False

if GEMINI_API_KEY and HAS_GEMINI:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        USE_GEMINI = True
        print("🌟 [起動モード] Gemini APIモード (クラウド翻訳)")
    except Exception as e:
        print(f"Geminiの初期化エラー: {e}")
else:
    print("🖥️ [起動モード] Ollamaモード (ローカル翻訳)")

def normalize_name(name):
    clean_name = name.lower().strip()
    return ALIAS_MAP.get(clean_name, clean_name)

def translate_text(text, is_name=False):
    if not text or text == "-" or len(text) < 2:
        return text
    
    if is_name:
        prompt = f"""You are a professional translator. Translate the English patch name to a concise Japanese noun phrase. 
Do NOT translate it as a full sentence. Do NOT use "Desu/Masu" or "しました". Output ONLY the translated Japanese text.

English: Hide shorts components
Japanese: ショート動画コンポーネントの非表示

English: {text}
Japanese:"""
    else:
        prompt = f"""You are a professional translator. Translate the English text to natural, polite Japanese (Desu/Masu form). 
Output ONLY the translated Japanese text. Do not add any greetings, explanations, alternative options, or English words.

English: Hide shorts components
Japanese: ショート動画のコンポーネントを非表示にします。

English: {text}
Japanese:"""

    translated = text

    if USE_GEMINI:
        try:
            response = gemini_model.generate_content(prompt)
            translated = response.text.strip()
        except Exception as e:
            return text
    else:
        for attempt in range(3):
            try:
                response = requests.post(OLLAMA_URL, json={
                    "model": MODEL_NAME, "prompt": prompt, "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 256, "top_p": 0.9}
                }, timeout=120) 
                result = response.json().get("response", "").strip()
                translated = result.split('\n')[0].replace("Japanese:", "").replace("English:", "").strip()
                break
            except Exception as e:
                if attempt < 2: time.sleep(2)
                else: return text

    if translated.startswith('"') and translated.endswith('"'):
        translated = translated[1:-1]
    if is_name:
        translated = translated.rstrip('。')

    return translated

def download_latest_patches():
    print("\n--- 🌐 最新のパッチリストをGitHubから取得中 ---")
    for filename, url in PATCH_URLS.items():
        if not url: continue
        try:
            print(f"[{filename}] をダウンロード中... ", end="")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, indent=4, ensure_ascii=False)
            print("✅ 成功")
        except Exception as e:
            print(f"❌ 失敗 (ローカルの既存ファイルを使用します) - {e}")

def load_translation_memory(file_path):
    memory = {}
    if not os.path.exists(file_path): return memory
    print(f"\n過去の翻訳データ ({file_path}) を読み込んでいます...")
    try:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            if "パッチ名 (EN / JA)" in df.columns and "説明 (原文)" in df.columns and "説明 (日本語)" in df.columns:
                for _, row in df.iterrows():
                    combo_name = str(row["パッチ名 (EN / JA)"])
                    desc_en = str(row["説明 (原文)"])
                    desc_ja = str(row["説明 (日本語)"])
                    orig_name, name_ja = combo_name.split(" / ", 1) if " / " in combo_name else (combo_name, combo_name)
                    norm_key = normalize_name(orig_name.split(" | ")[0])
                    memory[norm_key] = {"name_ja": name_ja, "desc_ja": desc_ja, "desc_en": desc_en}
        print(f"{len(memory)} 件の翻訳メモリをロードしました。")
    except Exception as e:
        print(f"翻訳メモリの読み込みに失敗: {e}")
    return memory

def get_patches(filename, target_type):
    patches = {}
    if not os.path.exists(filename): return patches
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            patch_list = data.get('patches', data) if isinstance(data, dict) else data if isinstance(data, list) else []
            for p in patch_list:
                original_name = p.get('name', 'Unknown')
                desc = p.get('description', '') or ""
                desc = desc.replace("\n", " ").replace("\r", "")
                compat = p.get('compatiblePackages')
                is_target = False
                if target_type == 'universal':
                    if not compat: is_target = True
                else:
                    target = 'com.google.android.youtube' if target_type == 'youtube' else 'com.google.android.apps.youtube.music'
                    if isinstance(compat, dict) and target in compat: is_target = True
                    elif isinstance(compat, list) and any((pkg.get('name') if isinstance(pkg, dict) else pkg) == target for pkg in compat): is_target = True
                
                if is_target:
                    patches[normalize_name(original_name)] = {"original_name": original_name, "description": desc}
    except: pass
    return patches

def get_sheet_data(category_name, target_type, files, trans_memory):
    print(f"\n--- 【{category_name}】解析開始 ---")
    rev_p, mor_p, and_p = get_patches(files[0], target_type), get_patches(files[1], target_type), get_patches(files[2], target_type)
    all_keys = sorted(list(set(rev_p.keys()) | set(mor_p.keys()) | set(and_p.keys())))
    if not all_keys: return None, None

    print(f"合計 {len(all_keys)} 件のパッチを処理します...")
    table_data, translate_count, skip_count, whitelist_hit = [], 0, 0, 0

    for i, norm_key in enumerate(all_keys, 1):
        original_names, desc_en = set(), ""
        for p_dict in [rev_p, mor_p, and_p]:
            if norm_key in p_dict:
                original_names.add(p_dict[norm_key]["original_name"])
                if not desc_en: desc_en = p_dict[norm_key]["description"]
            
        combined_original = " | ".join(sorted(list(original_names)))
        needs_translation, name_ja, desc_ja = True, "", ""

        if norm_key in trans_memory:
            old_data = trans_memory[norm_key]
            if norm_key in WHITELIST:
                name_ja, desc_ja, needs_translation = old_data["name_ja"], old_data["desc_ja"], False
                whitelist_hit += 1
            elif old_data["desc_en"] == desc_en:
                name_ja, desc_ja, needs_translation = old_data["name_ja"], old_data["desc_ja"], False

        if needs_translation:
            rep_name = list(original_names)[0]
            name_ja = translate_text(rep_name, is_name=True)
            desc_ja = translate_text(desc_en)
            translate_count += 1
        else:
            skip_count += 1
        
        final_name_col = f"{combined_original} / {name_ja}" if name_ja and name_ja != combined_original else combined_original
        rev_mark = "〇" if norm_key in rev_p else "-"
        mor_mark = "〇" if norm_key in mor_p else "-"
        and_mark = "〇" if norm_key in and_p else "-"

        if norm_key in CUSTOM_MARKS:
            if "revanced" in CUSTOM_MARKS[norm_key]: rev_mark = CUSTOM_MARKS[norm_key]["revanced"]
            if "morphe"   in CUSTOM_MARKS[norm_key]: mor_mark = CUSTOM_MARKS[norm_key]["morphe"]
            if "anddea"   in CUSTOM_MARKS[norm_key]: and_mark = CUSTOM_MARKS[norm_key]["anddea"]
        
        table_data.append([final_name_col, rev_mark, mor_mark, and_mark, desc_ja, desc_en])
        print(f"\r進捗: {i}/{len(all_keys)} (翻訳: {translate_count}, スキップ: {skip_count}, 固定: {whitelist_hit})", end="", flush=True)

    print("\nシート完了。")
    return table_data, ["パッチ名 (EN / JA)", f"ReVanced ({len(rev_p)})", f"Morphe ({len(mor_p)})", f"anddea ({len(and_p)})", "説明 (日本語)", "説明 (原文)"]

def main():
    download_latest_patches()
    files = ['revanced-dev-patches-list.json', 'MorpheApp-patches-list.json', 'andda-patches-list.json']
    trans_memory = load_translation_memory(EXCEL_FILE)

    yt_data, yt_head = get_sheet_data("YouTube", "youtube", files, trans_memory)
    ytm_data, ytm_head = get_sheet_data("YT Music", "ytmusic", files, trans_memory)
    univ_data, univ_head = get_sheet_data("Universal", "universal", files, trans_memory)

    print(f"\nExcel保存中: {EXCEL_FILE}")
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
        if yt_data: pd.DataFrame(yt_data, columns=yt_head).to_excel(writer, sheet_name='YouTube', index=False)
        if ytm_data: pd.DataFrame(ytm_data, columns=ytm_head).to_excel(writer, sheet_name='YT Music', index=False)
        if univ_data: pd.DataFrame(univ_data, columns=univ_head).to_excel(writer, sheet_name='Universal', index=False)
    print("✨ 更新が完了しました！")

if __name__ == "__main__":
    main()