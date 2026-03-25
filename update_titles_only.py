import pandas as pd
import os
import config
# ファイル名を直したので、これで正常に読み込めるようになります！
import compare_patches_12B_Quality as cp

def update_titles():
    if not os.path.exists(config.EXCEL_FILE):
        print(f"❌ {config.EXCEL_FILE} が見つかりません。先にメインスクリプトを実行してください。")
        return

    print(f"\n--- 🏷️ タイトル（パッチ名）のみ強制再翻訳モードを開始 ---")
    
    xls = pd.ExcelFile(config.EXCEL_FILE)
    sheets_data = {}
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if "パッチ名 (EN / JA)" not in df.columns:
            sheets_data[sheet_name] = df
            continue
            
        print(f"\n[{sheet_name}] シートのタイトルを処理中...")
        
        for index, row in df.iterrows():
            combo_name = str(row["パッチ名 (EN / JA)"])
            orig_names, old_ja = combo_name.split(" / ", 1) if " / " in combo_name else (combo_name, "")
            first_orig_name = orig_names.split(" | ")[0]
            
            # 💡 ここにあった「ホワイトリストのスキップ処理」を完全に削除しました！
            # これで全パッチのタイトルが容赦なく再翻訳されます。
            
            print(f"🔄 翻訳中: {first_orig_name} ... ", end="", flush=True)
            new_ja = cp.translate_text(first_orig_name, is_name=True)
            
            if new_ja and new_ja != orig_names:
                df.at[index, "パッチ名 (EN / JA)"] = f"{orig_names} / {new_ja}"
                print(f"✅ {new_ja}")
            else:
                df.at[index, "パッチ名 (EN / JA)"] = orig_names
                print(f"➖ 変更なし")
                
        sheets_data[sheet_name] = df
        
    print(f"\n💾 Excelファイルを上書き保存中: {config.EXCEL_FILE}")
    with pd.ExcelWriter(config.EXCEL_FILE, engine='openpyxl') as writer:
        for sheet_name, df in sheets_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    print("✨ タイトルの強制再翻訳が完了しました！")

if __name__ == "__main__":
    update_titles()