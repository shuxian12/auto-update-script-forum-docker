# auto-update-script-forum-docker

## 建置步驟

1. Clone repository
    ```shell
    git clone https://github.com/shuxian12/auto-update-script-forum-docker.git
    cd auto-update-script-forum-docker
    ```
2. 在 `auto-update-script-forum-docker\` 下新增 `.env` 檔案

    > :warning:
    > 請自行更改以下環境變數，如 `stroage container` 和 `search index`
    
    ```sh=
    AZURE_STORAGE_ACCOUNT='stj4pwo6tino56s'
    AZURE_STORAGE_CONTAINER='自行取名'
    AZURE_STORAGE_KEY='自己輸'
    AZURE_SEARCH_SERVICE='gptkb-j4pwo6tino56s'
    AZURE_SEARCH_INDEX='自行取名'
    AZURE_OPENAI_SERVICE='cog-j4pwo6tino56s'
    AZURE_OPENAI_KEY='自己輸'
    AZURE_OPENAI_CHATGPT_DEPLOYMENT='chat'
    AZURE_OPENAI_CHATGPT_MODEL='gpt-35-turbo'
    AZURE_KEY_CREDENTIAL='自己輸'
    KB_FIELDS_CONTENT='content'
    KB_FIELDS_CATEGORY='category'
    KB_FIELDS_SOURCEFILE='sourcefile'
    TENANT_ID='自己輸'
    
    ```
3. 建立 docker image
    > 此步驟約耗費 25 分鐘
    ```shell
    docker pull ubuntu:22.04
    docker build -t auto-update:1 . 
    ## image名稱可自行改變-> IMAGE名稱:TAG
    
    ## 確認image建立成功
    docker images
    ## REPOSITORY 和 TAG 有出現以下內容即成功建立
    ## REPOSITORY    TAG       IMAGE ID       CREATED         SIZE
    ## auto-update   1         04d0cca9c643   9 minutes ago   514MB
    ```
4. 將 `auto-update-doker.sh` 的內容加入到crontab排程中：
    
    ```shell
    crontab -e
    
    ## 會自動打開 vim 編輯器
    ## 到檔案最後一行，加入排程
    0 12 1,15 * * docker run --rm -v {script在本機端的絕對路徑}:/home/auto-update-script-forum-docker/script auto-update:1
    ## 如 /home/advantech/auto-update-script-forum-docker/script:/home/auto-update-script-forum-docker/script   
    ```
    > 初一十五會自動執行 docker 並更新資料
    > 當首次更新完成後，資料就會儲存在 `script/data` 中
    > 成功會出現以下文字
    > ![image](https://hackmd.io/_uploads/H1Gzq_Vrp.png)
5. 如果發現 docker 沒有正常更新，請根據以下步驟查看問題：
    * **create docker container**
    ```shell
    docker run -it --rm --name debug -v {script在本機端的絕對路徑}:/home/auto-update-script-forum-docker/script auto-update:1 /bin/bash
    ## docker run -it --rm --name debug -v /home/advantech/auto-update-script-forum-docker/script:/home/auto-update-script-forum-docker/script auto-update:1 /bin/bash
    ```
    * 應該會出現以 root 開頭的 terminal
    * ![image](https://hackmd.io/_uploads/BJzE2_ESa.png)
    * 手動執行更新程式，查看錯誤
        > 此步驟約耗費 10-15 分鐘
    ```shell
    cd /home/auto-update-script-forum-docker/script
    sh auto_update.sh
    ```
    * `ctrl d` 離開 container
    * 確認container是否已自動關閉
    ```shell
    docker ps -a
    
    ## 如果還有 container 還存在
    docker stop debug
    docker remove debug
    ```

## 問題參考
* [invoke-rc.d: could not determine current runlevel](https://github.com/microsoft/WSL/issues/2702)
