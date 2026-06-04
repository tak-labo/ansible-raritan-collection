# raritan.xerus Ansible Collection — Design Spec

**Date:** 2026-06-04  
**Updated:** 2026-06-04  
**Status:** 実装済み

---

## Context

Raritan PDU（電源管理ユニット）を Ansible で設定管理するための Collection を作る。
`raritan` pip パッケージ（v4.3.x）が公式 JSON-RPC クライアントを提供しており、これを利用する。
将来的に PDU 以外のデバイス（ネットワーク設定、ユーザー管理等）への拡張を予定している。

---

## Collection 概要

- **Namespace:** `raritan`
- **Collection name:** `xerus`
- **依存:** `raritan>=4.3.0`（pip パッケージ）

---

## Collection 構造

```
raritan/xerus/
├── galaxy.yml
├── README.md
├── requirements.txt
├── plugins/
│   ├── modules/
│   │   ├── datetime_config.py    # NTP・タイムゾーン設定（冪等）
│   │   ├── dns_config.py         # DNS サーバー・サーチドメイン設定（冪等）
│   │   ├── event_rule.py         # イベントエンジン ルール管理
│   │   ├── outlet_config.py      # アウトレット設定＋電源制御（冪等）
│   │   ├── pdu_config.py         # PDU 全体設定（冪等）
│   │   ├── pdu_facts.py          # PDU ファクト収集（読み取り専用）
│   │   ├── snmp_config.py        # SNMP v2/v3 設定（冪等）
│   │   ├── snmp_trap_action.py   # イベントエンジン SNMP トラップアクション管理
│   │   ├── syslog_action.py      # イベントエンジン Syslog アクション管理
│   │   └── user_account.py       # ユーザーアカウント＋SNMPv3 設定管理
│   └── module_utils/
│       └── raritan_client.py     # 接続・共通ロジック（全モジュールで再利用）
├── tests/
│   └── unit/
│       ├── test_datetime_config.py
│       ├── test_dns_config.py
│       ├── test_event_rule.py
│       ├── test_outlet_config.py
│       ├── test_pdu_config.py
│       ├── test_pdu_facts.py
│       ├── test_raritan_client.py
│       ├── test_snmp_config.py
│       ├── test_snmp_trap_action.py
│       ├── test_syslog_action.py
│       └── test_user_account.py
└── examples/
    ├── site.yml                              # ユーザー向けサンプル playbook
    ├── vars.yml.example                      # site.yml 用変数テンプレート
    ├── integration_test.yml                  # 統合テスト playbook
    └── integration_test_vars.yml.example     # 統合テスト用変数テンプレート
```

---

## アーキテクチャ

### module_utils/raritan_client.py

全モジュールが共用する接続レイヤー。

**責務:**
- `raritan.rpc.Agent` のインスタンス化（host / username / password / validate_certs）
- RPC 呼び出しの共通エラーハンドリング（接続失敗・認証エラー・タイムアウト）
- `get_agent(host, username, password, validate_certs) -> Agent` を公開

---

### モジュールパターン

モジュールは2つのパターンに分類される。

#### Pattern A: Settings モジュール（8種）

設定を取得して差分チェックし、変更があれば適用する冪等パターン。

```
getCfg() / getSettings()
  ↓ 現在の設定
差分チェック（desired vs current）
  ↓ 差分あり
setCfg() / setSettings()
  ↓
changed=True / changed=False
```

対象モジュール: `datetime_config`, `dns_config`, `outlet_config`, `pdu_config`, `snmp_config`, `event_rule`, `snmp_trap_action`, `syslog_action`

#### Pattern B: Resource モジュール（1種）

`state: present/absent` でリソースのライフサイクルを管理するパターン。

```
getAccountNames()
  ↓ ユーザー一覧
state=absent → deleteAccount()
state=present（新規）→ 2ステップ作成（後述）
state=present（既存）→ 差分チェック → updateAccountFull()
```

対象モジュール: `user_account`

**user_account の API 制約と 2ステップ作成:**

`createAccountFull()` は `AUTH_PRIV` / `AUTH_NO_PRIV` の secLevel を作成時に設定できない（rc=5 を返す）。
回避策: UUID ベースの一時パスワードとブランク `UserInfo()` で作成した後、即座に `updateAccountFull()` で本パスワードと SNMPv3 設定を適用する。

```python
temp_pw = 'Tmp' + uuid.uuid4().hex
rc = mgr.createAccountFull(target_user, temp_pw, usermgmt.UserInfo())
user = usermgmt.User('/auth/user/<name>', agent)
info = user.getInfo()
# SNMPv3 設定を info に適用
rc2 = user.updateAccountFull(new_password, info)
```

---

## RPC ターゲット一覧

| モジュール | RPC クラス | ターゲットパス |
|---|---|---|
| `datetime_config` | `datetime.DateTime` | `/datetime` |
| `dns_config` | `net.Net` | `/net`（`/net/manager` ではない） |
| `event_rule` | `eventengine.EventEngine` | `/eventengine` |
| `outlet_config` | `outlet.Outlet` | `/outlet/<n>`（1始まり） |
| `pdu_config` | `pdu.Pdu` | `/pdu/0` |
| `pdu_facts` | `pdumodel.Pdu` | `/model/pdu/0` |
| `snmp_config` | `snmp.Snmp` | `/snmp` |
| `snmp_trap_action` | `eventengine.EventEngine` | `/eventengine` |
| `syslog_action` | `eventengine.EventEngine` | `/eventengine` |
| `user_account` | `usermgmt.UserManager` / `usermgmt.User` | `/auth/user` / `/auth/user/<name>` |

---

## 各モジュール仕様

### datetime_config

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `host` / `username` / `password` | str | ✓ | 接続情報 |
| `validate_certs` | bool | — | TLS 証明書検証（default: true） |
| `timezone` | str | — | タイムゾーン表示名（例: `"(UTC+09:00) Osaka, Sapporo, Tokyo"`） |
| `protocol` | str | — | `ntp` / `static` |
| `ntp_server1` | str | — | プライマリ NTP サーバー |
| `ntp_server2` | str | — | セカンダリ NTP サーバー |

タイムゾーンは `getZoneInfos(False)` で取得した表示名（109件）から ID に変換して適用。

---

### dns_config

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `servers` | list[str] | — | DNS サーバー IP アドレスリスト（順序不問） |
| `search_suffixes` | list[str] | — | DNS サーチドメインリスト（順序不問） |
| `prefer_ipv6` | bool | — | IPv6 DNS リゾルバ優先 |

`settings.common.dns` 配下の設定を操作する。

---

### event_rule / syslog_action / snmp_trap_action

イベントエンジンの設定を `getActionList()` / `createAction()` / `updateAction()` / `deleteAction()` で管理。
`name` パラメータを冪等キーとして使用（名前で存在チェック）。

**event_rule** 追加パラメータ:

| パラメータ | 説明 |
|---|---|
| `action_names` | アクション名リスト（ID に自動解決） |
| `event_id` | イベント ID パターン（`["**"]` で全イベント） |
| `match_type` | `asserted` / `deasserted` / `both` |
| `enabled` / `auto_rearm` | ルールの有効化・自動リアーム |

---

### outlet_config

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `outlet` | int | ✓ | アウトレット番号（1 始まり） |
| `name` | str | — | アウトレット名 |
| `state` | str | — | `on` / `off` / `cycle` / `unchanged`（default: unchanged） |
| `startup_state` | str | — | `on` / `off` / `last_known` |
| `cycle_delay` | int | — | 電源サイクル遅延（秒） |
| `non_critical` | bool | — | 負荷削減対象外フラグ |

`state: cycle` は常に `changed=True`（アクション的操作のため冪等でない）。

---

### pdu_config

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `name` | str | — | PDU 名 |
| `cycle_delay` | int | — | アウトレット電源サイクル遅延（秒） |
| `startup_state` | str | — | `on` / `off` / `last_known` |

---

### snmp_config

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `v2_enabled` / `v3_enabled` | bool | — | SNMP v2/v3 有効化 |
| `read_community` / `write_community` | str | — | v2 コミュニティ文字列 |
| `sys_contact` / `sys_name` / `sys_location` | str | — | SNMP システム情報 |

---

### user_account

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `target_user` | str | ✓ | 管理対象ユーザー名 |
| `new_password` | str | — | パスワード（作成・更新時に必須） |
| `snmp_v3_enabled` | bool | — | SNMPv3 有効化 |
| `sec_level` | str | — | `no_auth_no_priv` / `auth_no_priv` / `auth_priv` |
| `auth_protocol` | str | — | `md5` / `sha1` / `sha256` 等 |
| `priv_protocol` | str | — | `des` / `aes128` / `aes256` 等 |
| `use_password_as_auth_passphrase` | bool | — | パスワードを認証パスフレーズとして使用 |
| `auth_passphrase` / `priv_passphrase` | str | — | 明示的なパスフレーズ（書き込み専用） |
| `state` | str | — | `present`（default） / `absent` |

パスフレーズは読み取り不可のため冪等チェック対象外。

---

## データフロー

### Settings パターン

```
Playbook
  ↓ パラメータ
module (datetime_config / dns_config / etc.)
  ↓ get_agent()
raritan_client (module_utils)
  ↓ raritan.rpc.Agent
Raritan PDU (HTTPS JSON-RPC)
  ↓ getCfg() / getSettings()
module
  ↓ 差分チェック（desired vs current）
  差分なし → exit_json(changed=False)
  差分あり → setCfg() / setSettings()
           → exit_json(changed=True)
```

### Resource パターン（user_account）

```
Playbook
  ↓ state=present/absent, target_user
user_account module
  ↓ UserManager.getAccountNames()
  state=absent かつ存在する → deleteAccount() → changed=True
  state=present かつ不在   → 2ステップ作成 → changed=True
  state=present かつ存在   → 差分チェック → updateAccountFull() / 変更なし
```

---

## エラーハンドリング

- 接続失敗 → `module.fail_json(msg="Connection failed: ...")`
- 認証失敗 → `module.fail_json(msg="Authentication failed")`
- アウトレット番号範囲外 → `module.fail_json(msg="Outlet N not found")`
- RPC エラーコード → `module.fail_json(msg="<operation> failed with error code: N")`
- 不明なタイムゾーン名 → `module.fail_json(msg='Unknown timezone "...". Available: [...]')`

---

## テスト方針

### ユニットテスト（`tests/unit/`）

- `unittest.mock` で `get_agent` と SDK クラスをパッチ
- モジュールファイルレベルで import された SDK モジュールをまるごとパッチ（例: `patch('dns_config.net')`）
- 各モジュールで以下をカバー:
  - 変更なし（冪等）
  - 各パラメータの変更検出
  - check_mode（setSettings/setCfg 未呼び出し）
  - エラーコード → fail_json
  - 接続エラー → fail_json

### 統合テスト（`examples/integration_test.yml`）

- 実機 PDU（192.168.200.13）に対して実行
- 各モジュールのセクション構成: 既知状態確立 → 冪等確認 → 変更検出 → 元設定に復元
- タスク名は `[module_name] <説明>` 形式（`--start-at-task` でセクション指定可能）

```bash
# 全テスト実行
cp examples/integration_test_vars.yml.example examples/integration_test_vars.yml
cp plugins/modules/*.py /tmp/ansible_collections/raritan/xerus/plugins/modules/
ANSIBLE_COLLECTIONS_PATH=/tmp/ansible_collections \
  uv run ansible-playbook examples/integration_test.yml
```

---

## Playbook 使用例

```yaml
# examples/site.yml（抜粋）
- name: Configure Raritan PDU
  hosts: localhost
  gather_facts: false
  vars_files:
    - vars.yml

  tasks:
    - name: Set PDU name and cycle delay
      raritan.xerus.pdu_config:
        host: "{{ pdu_host }}"
        username: "{{ pdu_user }}"
        password: "{{ pdu_pass }}"
        validate_certs: "{{ validate_certs }}"
        name: "{{ pdu_name }}"
        cycle_delay: "{{ pdu_cycle_delay }}"

    - name: Configure NTP and timezone
      raritan.xerus.datetime_config:
        host: "{{ pdu_host }}"
        username: "{{ pdu_user }}"
        password: "{{ pdu_pass }}"
        validate_certs: "{{ validate_certs }}"
        timezone: "{{ timezone }}"
        protocol: ntp
        ntp_server1: "{{ ntp_server1 }}"
```

---

## 将来の拡張候補

| モジュール | 対象 raritan.rpc モジュール | 概要 |
|---|---|---|
| `security_config` | `raritan.rpc.security` | TLS・パスワードポリシー等のセキュリティ設定 |
| `network_config` | `raritan.rpc.net` | インターフェース・VLAN 等のネットワーク設定 |

---

## 検証方法

```bash
# ユニットテスト（全件）
uv run pytest

# ユニットテスト（単一ファイル）
uv run pytest tests/unit/test_dns_config.py -v

# 統合テスト（全件）
cp plugins/modules/*.py /tmp/ansible_collections/raritan/xerus/plugins/modules/
ANSIBLE_COLLECTIONS_PATH=/tmp/ansible_collections \
  uv run ansible-playbook examples/integration_test.yml

# 統合テスト（特定モジュールから）
ANSIBLE_COLLECTIONS_PATH=/tmp/ansible_collections \
  uv run ansible-playbook examples/integration_test.yml \
  --start-at-task "[datetime_config] apply test settings"
```
