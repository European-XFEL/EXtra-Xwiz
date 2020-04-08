import os
import toml
from .templates import CONFIG

conf_path = os.path.join(os.getcwd(), '.xwiz_conf.toml')


def create_file():
    with open(conf_path, 'w') as f:
        f.write(CONFIG)


def load_from_file():
    conf = toml.load(conf_path)
    return conf

