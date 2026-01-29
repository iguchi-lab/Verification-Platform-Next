# 開発時における Git ブランチ戦略

## 概要

本リポジトリは `BRI-EES-House/pyhees` からフォークしており、独自機能を追加しながら開発を進めています。開発した独自機能はプラットフォームにて公開され、委員による検証を進めています。

## リポジトリの種類

本プロジェクトは 3 つのリポジトリで構成されています。

BRI-EES-House/pyhees: 建築研究所
┣ iguchi-lab/pyhees: 井口研究室
┗ izumi-system-development/pyhees: イズミコンサルティング

## 開発からリリースの流れ

開発した機能は以下の流れでユーザーに公開されます：

```mermaid
sequenceDiagram
    participant Dev as 開発環境
    participant Izumi as izumi-system-development
    participant Iguchi as iguchi-lab
    participant Platform as プラットフォーム

    Dev->>Izumi: 1. 開発ブランチ feature
    Izumi->>Izumi: 2. 検証ブランチ jjj-experiment-development へPR
    Izumi->>Platform: 3. 動作確認
    Izumi->>Iguchi: 4. jjj-experiment-v3.x へPR
    Iguchi->>Platform: 5. 委員による検証
    Izumi->>Iguchi: 6. Fetch & Pull
```

## ブランチの種類と役割

### 1. リリースブランチ jjj-experiment-v3.x

**役割**: 特定バージョンの upstream に対する安定版カスタム機能を提供

**特徴**:
- ✅ プラットフォームで委員へ公開され検証される
- ✅ upstream の対応バージョンが明確（例: `jjj-experiment-v3.8`）
- ✅ 検証ブランチからマージされた機能を統合
- ⚠️ 直接このブランチでの開発は避け PR によって更新する

**リリースまでの開発フロー**:

```mermaid
gitGraph
    commit id: "v3.8" tag: "upstream"
    branch jjj-experiment-v3.8
    checkout jjj-experiment-v3.8
    commit id: "stable-1"
    branch jjj-experiment-develop
    checkout jjj-experiment-develop
    commit id: "develop-base"
    checkout jjj-experiment-v3.8
    branch feature/func-a
    checkout feature/func-a
    commit id: "work-1"
    commit id: "work-2"
    checkout jjj-experiment-develop
    merge feature/func-a tag: "PR@izumi-system-development"
    commit id: "統合テスト"
    checkout jjj-experiment-v3.8
    merge jjj-experiment-develop tag: "PR@iguchi-lab"
    commit id: "stable-2"
```

### 2. 検証ブランチ jjj-experiment-develop

**役割**: 実験的な機能や複数機能の統合テストを行う開発用ブランチ

**特徴**:
- ✅ 新機能の統合テスト環境
- ✅ 複数の feature を統合して動作確認
- ⚠️ **不安定な状態になる可能性がある**
- ⚠️ **リリースブランチの新バージョンが作られる度に作り直す必要がある**

**用途**:
- 複数機能の組み合わせ動作確認
- 統合テスト環境
- デモ環境

**ライフサイクル（バージョンアップ時の作り直し）**:

リリースブランチのバージョンアップがされる度に作り直す。
その際、ローカルだけでなくリモートからもブランチを一旦削除する。
他開発者への影響を考慮する。

```mermaid
gitGraph
    commit id: "v3.8" tag: "upstream"
    branch jjj-experiment-v3.8
    checkout jjj-experiment-v3.8
    commit id: "custom-1"
    commit id: "custom-2"
    branch jjj-experiment-develop
    checkout jjj-experiment-develop
    commit id: "test-a"
    commit id: "test-b"
    checkout main
    commit id: "v3.9" tag: "upstream更新"
    checkout jjj-experiment-v3.8
    merge jjj-experiment-develop
    branch jjj-experiment-v3.9
    checkout jjj-experiment-develop
    commit id: "DELETE develop" type: REVERSE
    checkout jjj-experiment-v3.9
    merge main tag: "マージ追従"
    branch jjj-experiment-develop2
    checkout jjj-experiment-develop2
    commit id: "develop 再作成" type: HIGHLIGHT
```

### 3. main ブランチ

**役割**: 開発に使用せず upstream（`BRI-EES-House/pyhees`）と常に一致する

```mermaid
gitGraph

commit id: "v3.8" tag: "izumi-system-development | iguchi-lab | BRI-EES-House"
```

**特徴**:
- ✅ upstream の最新状態を反映
- ⚠️ このブランチで直接開発は行わない
- ⚠️ カスタム機能は含まれない

**用途**:
- upstream との差分確認
- バージョンアップ時のベースとして使用
