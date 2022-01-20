import os
import subprocess


def local_wc(flags):
    home = os.getcwd()
    args = ("python3 wc.py -i ff3.smc -o seedbot.smc " + flags)
    os.chdir('../worldscollide')
    try:
        os.mkdir('zips')
    except FileExistsError:
        pass
    try:
        subprocess.check_call(args, shell=True)
    except subprocess.CalledProcessError:
        os.chdir(home)
        raise AttributeError
