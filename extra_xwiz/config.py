import os
import toml

conf_path = os.path.join(os.getcwd(), 'xwiz_conf.toml')


def create_file(config_template):
    with open(conf_path, 'w') as f:
        f.write(config_template)
    print('Configuration written to', conf_path)


def load_from_file():
    conf = toml.load(conf_path)
    print('Configuration loaded.')
    return conf
