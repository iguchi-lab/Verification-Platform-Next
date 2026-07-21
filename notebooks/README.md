# Notebooks

- `Verification_Platform_Next.ipynb`: アプリのインストールと起動だけを行うColabランチャーです。
- `legacy/Verification_Platform_260715_Gradio.ipynb`: モノレポ移行開始時点の動作版です。

入力定義や計算ロジックをノートブックへ直接追加しないでください。

Colabランチャーは依存関係のインストール後にPhase 5数値回帰を実行し、代表2ケースが固定基準と一致した場合だけアプリを起動します。ローカルやCodex Cloudでも同じ確認を次のコマンドで実行できます。

セットアップセルは必ず `/content` へ戻り、既存cloneがあればfast-forward更新して再利用します。アプリのeditable installからモノレポ内の `verification-core` と `pyhees-jjj` も解決されるため、これらを同じpipコマンドへ重複指定しません。

```bash
python scripts/run_phase5_regression.py
```
