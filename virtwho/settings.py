"""Define and instantiate the configuration class for virtwho-test."""
import os
from configparser import ConfigParser


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Configure:
    """Configure class is able to parse and handle local or remote ini
     file.
    """

    def __init__(self, local_file, remote_ssh=None, remote_file=None):
        """Local_file will be read and parsed after call the class.
        If remote_ssh and remote_file are provided, the local_file
        will be uploaded to remote server as remote_file.

        :param local_file: A local file path for reading and setting.
            File will be created if not available.
        :param remote_ssh: Access to remote file.
        :param remote_file: A remote file path where the uploaded file
            will be placed.
        """
        self.local_file = local_file
        self.remote_file = remote_file
        self.remote_ssh = remote_ssh
        self.config = ConfigParser(dict_type=AttrDict)
        self.config.read(self.local_file)
        self.save()

    def save(self):
        """Save changes to local_file, and upload the local_file to
        remote server if remote_ parameters provided to achieve updating
        remote file.
        """
        for key in self.config._sections.keys():
            setattr(self, key, getattr(self.config._sections, key))
        with open(self.local_file, 'w') as f:
            self.config.write(f, space_around_delimiters=False)
        if self.remote_ssh and self.remote_file:
            self.remote_ssh.put_file(self.local_file, self.remote_file)

    def update(self, section, option, value):
        """Used to add section, add option or update option in a file.
        :param section: Section to look for. It will be added if not
            exist.
        :param option: Option to update. It will be added if not exist.
        :param value: Value to update for the option.
        """
        # print(f'UPDATE [{section}]:{option}={value}')
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.save()

    def delete(self, section, option=None):
        """Used to remove section or remove option in a file
        :param section: Section to look for. It will be removed when no
            option provided.
        :param option: Option to remove.
        """
        # print(f'DELETE [{section}]:{option}=')
        if option is None:
            self.config.remove_section(section)
        else:
            self.config.remove_option(section, option)
        self.save()


DOCS_DIR = os.path.join(os.path.realpath(os.path.join(
    os.path.dirname(__file__),
    os.pardir)),
    "docs"
    )

TEMP_DIR = os.path.join(os.path.realpath(os.path.join(
    os.path.dirname(__file__),
    os.pardir)),
    "temp"
    )

TEST_DATA = os.path.join(os.path.realpath(os.path.join(
    os.path.dirname(__file__),
    os.pardir)),
    "virtwho.ini"
    )

config = Configure(TEST_DATA)
