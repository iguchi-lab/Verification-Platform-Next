# pyhees-jjj migration boundary

計算エンジン本体は、履歴を保持した移行を行うまでこのディレクトリへコピーしません。

現在、`apps/gradio/pyproject.toml` は次の固定コミットをGit依存として使用します。

```text
iguchi-lab/pyhees-jjj@0f91ba8381df1b4960557b92b39339385cc9009f
```

履歴移行後、このファイルはエンジン本体とそのパッケージ設定に置き換えます。
