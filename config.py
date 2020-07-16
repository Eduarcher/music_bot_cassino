import toml
import logging
import os

EXAMPLE_CONFIG = """\"token\"=\"\" # the bot's token
\"prefix\"=\"!\" # prefix used to denote commands
"extensions"=['music']
"""


class Config:
    def __init__(self, path="./config.toml"):
        self.__params = self.__load_config(path)

    @property
    def params(self):
        return self.__params

    def __load_config(self, path):
        """Loads the config from `path`"""
        if os.path.exists(path) and os.path.isfile(path):
            config = toml.load(path)
            return config
        else:
            with open(path, "w") as config:
                config.write(EXAMPLE_CONFIG)
                logging.warning(
                    f"No config file found. Creating a default config file at {path}"
                )
            return self.__load_config(path=path)
