#!/bin/sh

DATE=$(date +'%Y-%m-%d_%H:%M:%S')
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
cd $SCRIPTPATH

# start scraping forum
echo '+--------------------------------------+'
echo '| Start scraping forum.aim-linux.advantech.com |'
/home/advantech/anaconda3/bin/python download_forum.py --folder 'forum/' --update > "../log/forum/$DATE.log"

# start scraping wiki
echo '+--------------------------------------+'
echo '| Start scraping wiki.aim-linux.advantech.com |'
/home/advantech/anaconda3/bin/python download_wiki.py --folder 'wiki/' --update --url 'http://ess-wiki.advantech.com.tw/view/RISC'  > "../log/wiki/$DATE.log"

# start updating index
echo '+--------------------------------------+'
echo '| Start updating index |'
sh prepdocs.sh --data_path "/home/advantech/auto-update-script-forum/script/forum/"
sh prepdocs.sh --data_path "/home/advantech/auto-update-script-forum/script/wiki/"

# end
echo '+--------------------------------------+'
echo '| Done |'
