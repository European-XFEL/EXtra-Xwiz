import os
from . import config


def virtualize():
    pass

def manage_workflow(homedir, workdir, interactive=False):

    print(' xWiz - EXtra tool for pipelined SFX workflows')

    if not os.path.exists(f'{homedir}/.xwiz_conf.toml'):
        print('configuration file is not present, will be created.')
        config.create_file()
    else:
        print('configuration file is present.')
    conf = config.load_from_file()
    #print(conf)
    print('TASK: create virtual data set')
    data_path = conf['']
    if interactive:
        data_path = 


def main(argv=None):
    ap = ArgumentParser(prog="extra-xwiz")
    ap.add_argument(
        "-i", "--interactive", help="screen through configuration"
        " interactively",
        action='store_true'
    )
    args = ap.parse_args(argv)
    homedir = os.path.join('/home', os.getlogin())
    workdir = os.getcwd()
    manage_workflow(homedir, workdir, interactive=args.interactive)


