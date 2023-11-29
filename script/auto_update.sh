#!/bin/sh

DATE=$(date +'%Y-%m-%d_%H:%M:%S')
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
cd $SCRIPTPATH

# check if having forum and wiki folder
if [ ! -d "data" ]; then
    mkdir data
    cp -r ../data/forum ./data/
    cp -r ../data/wiki ./data
fi

# start scraping forum
echo '+--------------------------------------+'
echo '| Start scraping forum.aim-linux.advantech.com |'
python3 download_forum.py --folder 'data/forum/' --update > "../log/forum/$DATE.log"

# start scraping wiki
echo '+--------------------------------------+'
echo '| Start scraping wiki.aim-linux.advantech.com |'
python3 download_wiki.py --folder 'data/wiki/' --update --url 'http://ess-wiki.advantech.com.tw/view/RISC'  > "../log/wiki/$DATE.log"

# start updating index
echo '+--------------------------------------+'
echo '| Start updating index |'
sh prepdocs.sh --data_path "/home/auto-update-script-forum-docker/script/data/forum/"
sh prepdocs.sh --data_path "/home/auto-update-script-forum-docker/script/data/wiki/"

# end
echo '+--------------------------------------+'
echo '| Done |'
