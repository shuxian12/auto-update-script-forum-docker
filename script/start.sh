#!/bin/sh

DATE=$(date +'%Y-%m-%d_%H:%M:%S')
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
cd $SCRIPTPATH
mkdir ../data

# # start scraping forum
echo '+--------------------------------------+'
echo '| Start scraping forum.aim-linux.advantech.com |'
mkdir ../data/forum
python3 download_forum.py --folder '../data/forum/' --new

# start scraping wiki
echo '+--------------------------------------+'
echo '| Start scraping wiki.aim-linux.advantech.com |'
mkdir ../data/wiki
python3 download_wiki.py --folder '../data/wiki/' --new --url 'http://ess-wiki.advantech.com.tw/view/RISC'

# start updating index
echo '+--------------------------------------+'
echo '| Start updating index |'
sh prepdocs.sh --data_path "/home/auto-update-script-forum-docker/data/forum/"
sh prepdocs.sh --data_path "/home/auto-update-script-forum-docker/data/wiki/"

# end
echo '+--------------------------------------+'
echo '| Done |'
