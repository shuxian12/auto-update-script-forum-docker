#!/bin/sh

DATE=$(date +'%Y-%m-%d_%H:%M:%S')
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
cd $SCRIPTPATH

# # start scraping forum
echo '+--------------------------------------+'
echo '| Start scraping forum.aim-linux.advantech.com |'
mkdir forum
python download_forum.py --folder 'forum/' --new

# start scraping wiki
echo '+--------------------------------------+'
echo '| Start scraping wiki.aim-linux.advantech.com |'
mkdir wiki
python download_wiki.py --folder 'wiki/' --new --url 'http://ess-wiki.advantech.com.tw/view/RISC' 

# start updating index
echo '+--------------------------------------+'
echo '| Start updating index |'
sh prepdocs.sh --data_path "/home/advantech/auto-update-forum-bot/script/forum/"
sh prepdocs.sh --data_path "/home/advantech/auto-update-forum-bot/script/wiki/"

# end
echo '+--------------------------------------+'
echo '| Done |'
