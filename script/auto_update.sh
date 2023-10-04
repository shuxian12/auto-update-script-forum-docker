#!/bin/sh

SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
cd $SCRIPTPATH

# start scraping forum
echo '+--------------------------------------+'
echo '| Start scraping forum.aim-linux.advantech.com |'
python download_forum.py --folder 'forum/' --update    

# start scraping wiki
echo '+--------------------------------------+'
echo '| Start scraping wiki.aim-linux.advantech.com |'
python download_wiki.py --folder 'wiki/' --update --url 'http://ess-wiki.advantech.com.tw/view/RISC'

# start updating index
echo '+--------------------------------------+'
echo '| Start updating index |'
sh prepdocs.sh --data_path "/home/advantech/auto-update-forum-bot/script/forum/"
sh prepdocs.sh --data_path "/home/advantech/auto-update-forum-bot/script/wiki/"

# end
echo '+--------------------------------------+'
echo '| Done |'
