https://user-images.githubusercontent.com/122780337/232202142-94b9c90a-605c-4588-9ad2-28a800801ad6.mov

# 概要
アタックツリー描画ツール．パーツ作成スクリプト[CATPEC](https://github.com/RATTATAlab/CATPEC)が生成するリストをインポートすると，CAPEC攻撃パターンを使用しながらアタックツリーが作成できる他，本ツールで作成した別のアタックツリーからもパーツを検索して再利用が可能．
RATTATA, Reusable Attack Trees Tool Accessible To All.
らったった．

# 対応OS
- Windows 10
- Mac OS (Big Sur, Monterey)

# 実行環境
- 事前に[graphviz](https://graphviz.org)のインストールが必要
    - [ダウンロード方法](https://graphviz.org/download/)
        - やり方によってはパスの設定も併せて必要
        - windowsの場合，chcolateyで1コマンドでできた
- Windowsの例
    - powershellを管理者で起動して以下のコマンドを実行
        ```
        cinst graphviz
        ```
        - cinstが無いと言われた場合，パッケージ管理ソフトのchocolateyをインストールしてから再度実行
            ```
            PS C:\> Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
            ```
    - 正常にインストールされたか確認（バージョン情報が出力されればOK）
        ```
        dot -V
        ```
- Macの例
    - ターミナルで以下のコマンドを実行（試していない）
        ```
        sudo port install graphviz
        ```
    - Brewでも良い（私はこっちでやった）
        ```
        brew install graphviz
        ```
        - Brewでインストールした場合，必要ライブラリが足りていない場合があるかも
            ```
            brew info graphviz
            ```
        - 出力結果の例
            ```
            Build: autoconf ✔, automake ✔, bison ×, pkg-config ✔
            Required: gd ✔, gts ✔, libpng ✔, librsvg ✔, libtool ✔, pango ✔
            ```
        - ×がついているライブラリがあったらインストールする
            ```
            brew install bison
            ```
    - 正常にインストールされたか確認（バージョン情報が出力されればOK）
        ```
        dot -V
        ```

# パーツリストのインポート
[CATPEC](https://github.com/RATTATAlab/CATPEC)により作成したアタックツリーパーツのリストをインポートできます．
CATPECから出力されたxmlファイルをローカルに作成されるフォルダRATTATA/data/capec/に保存の上，PartsView.pyのソースコードに合わせてリネームしてください．

# 自動作成されるファイル等
- 隠しフォルダ
    - Windows : [~\AppData\Local\Programs\RATTATA]
    - Max : ['~/Library/RATTATA]
- 設定ファイル
    - [RATTATA/config.ini]をいじると色々変えられます．
    - 動かなくなったらiniファイルを削除してRATTATAを再起動すると元に戻ります．

# 操作方法
## キャンバス（右画面）
- スクロールバーで画像の移動可能
- 画像を直接ドラッグすることも可能

## アウトライン（左画面）
- ノード作成等はショートカットもしくは左クリックで可能
- ショートカットはツールバーの「編集」を見てね．

## パーツ検索ウィンドウ（メニューから）
- メニューの「再利用」->「パーツ検索ビューの表示」でアタックツリーパーツを検索可能（事前にパーツリストをインポートする必要あり）
- 別に作成したアタックツリーのデータファイル（RATTATA/data/output/に保存されているもの）で使用しているパーツも検索可能

## ターミナル
- 出さないと動かないので出しているだけなのでお気になさらず
- アプリケーションを終了したらバツで閉じてください
