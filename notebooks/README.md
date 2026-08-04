# Notebooks

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/iguchi-lab/Verification-Platform-Next/blob/main/notebooks/Verification_Platform_Next.ipynb)

- `Verification_Platform_Next.ipynb`: アプリのインストールと起動だけを行うColabランチャーです。
- `legacy/Verification_Platform_260715_Gradio.ipynb`: モノレポ移行開始時点の動作版です。

入力定義や計算ロジックをノートブックへ直接追加しないでください。

## Colabでの起動手順

1. 上の **Open in Colab** をクリックします。
2. Colabのメニューから **ランタイム > すべてのセルを実行** を選びます。
3. 最初のコードセルによるリポジトリの取得・更新とインストールが終わるまで待ちます。
4. 最後のコードセルに次のような行が表示されたら、`gradio.live`の公開リンクを
   クリックします。

   ```text
   Running on public URL: https://xxxxxxxxxxxxxxxxxx.gradio.live
   ```

5. 開いた画面で条件を入力し、計算を実行します。アプリを使用している間は、
   Colabの最後のコードセルを停止しないでください。

`http://0.0.0.0:7860`や`http://127.0.0.1:7860`はColab内部のアドレスなので、
手元のブラウザからは開けません。必ず`https://...gradio.live`を使用してください。

公開リンクは一時的で、ランタイムを再起動するとURLが変わります。接続が切れた場合は
最後のコードセルを再実行し、新しく表示された公開リンクを開いてください。

notebookのコードセルは、セットアップとアプリ起動の2つです。通常利用では両方を
実行します。Phase 5数値回帰は通常の起動には不要なため、notebookの既定手順には
含めていません。

## 開発時の数値回帰

計算エンジンまたは入力契約を変更した場合は、アプリの起動とは別に次を実行します。

```bash
python scripts/run_phase5_regression.py
```

セットアップセルは`/content`へ戻り、既存cloneがあればfast-forward更新して再利用
します。アプリのeditable installからモノレポ内の`verification-core`と
`pyhees-jjj`も解決されるため、同じpipコマンドへの重複指定は不要です。
