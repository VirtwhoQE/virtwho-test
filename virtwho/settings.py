"""Define and instantiate the configuration class for virtwho-test."""
import os
from configparser import ConfigParser
from virtwho.ssh import SSHConnect


def get_project_root():
    """Return the path to the virtwho-test project root directory.

    :return: A directory path.
    :rtype: str
    """
    return os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))


class ConfHandler(object):
    """ConfigParser able to read INI file and configure content."""

    def __init__(self, path):
        self.config_parser = ConfigParser()
        try:
            with open(path) as handler:
                self.config_parser.read_file(handler)
        except:
            pass

    def get(self, section, option, default=None):
        """Read an option from a section of a INI file.
        The default value will return if the look up option is not available.
        :param section: Section to look for.
        :param option: Option to look for.
        :param default: The value that should be used if the option is not defined.
        """
        try:
            return self.config_parser.get(section, option)
        except:
            return default

    def set(self, section, option=None, value=None):
        """Update option's value in a INI file
        :param section: Section will be added if not available
        :param option: Option will be added if not available
        :param value: The value that should be updated for using
        """
        try:
            if not self.has_section(section):
                self.config_parser.add_section(section)
            if option and option is not '':
                self.config_parser.set(section, option, value)
        except:
            pass

    def write(self, file_path):
        """Write the update information to an INI file
        :param file_path: The INI file path
        """
        try:
            with open(file_path, "w") as handler:
                self.config_parser.write(handler)
        except:
            pass

    def remove_option(self, section, option):
        """Remove an option from INI file
        """
        try:
            self.config_parser.remove_option(section, option)
        except:
            pass

    def has_section(self, section):
        """Check if section exist."""
        return self.config_parser.has_section(section)


class FeatureSettings(object):
    """Settings related to a feature.
    Create an instance of this class and assign attributes to map to the feature
    options.
    """

    def read(self, reader):
        """Subclasses must implement this method in order to populate itself
        with expected settings values.
        :param reader: An INIReader instance to read the settings.
        """
        raise NotImplementedError('Subclasses must implement read method.')

    def validate(self):
        """Subclasses must implement this method in order to validate the
        settings and raise ``ImproperlyConfigured`` if any issue is found.
        """
        raise NotImplementedError('Subclasses must implement validate method.')


class Settings(object):
    """Settings representation of virtwho-test project"""

    def __init__(self):
        self.configured = False

    def configure(self, settings_file):
        """Read the settings file and parse the configuration.
        :param settings_file: File to read. The file path is the project root.
        """

        self.file_path = os.path.join(get_project_root(), settings_file)
        self.reader = ConfHandler(self.file_path)
        attrs = map(
            lambda attr_name: (attr_name, getattr(self, attr_name)),
            dir(self)
        )

        feature_settings = filter(
            lambda tpl: isinstance(tpl[1], FeatureSettings),
            attrs
        )
        for name, settings in feature_settings:
            if self.reader.has_section(name):
                settings.read(self.reader)

        self.configured = True


class Configure(Settings):
    """Configure class able to read and handle any local or remote ini file.
    """

    def __init__(self, local_file, remote_ssh=None, remote_file=None):
        """local_file will be read and parsed after call the class.
        :param local_file: Local file under project root for reading and configuring.
            It can be an already existing file or downloaded file from remote server.
        :param remote_ssh: The connection access to remote server.
            The format is {'host':'', 'user':'', 'pwd':''}
        :param remote_file: File on remote server with absolute path.
        """
        if remote_ssh and remote_file:
            self.remote_server = remote_ssh['host']
            self.remote_username = remote_ssh['user']
            self.remote_password = remote_ssh['pwd']
            self.local_file = os.path.join(get_project_root(), local_file)
            self.remote_file = remote_file
            self.sftp = SSHConnect(host=self.remote_server,
                                   user=self.remote_username,
                                   pwd=self.remote_password)
            self.sftp.get_file(self.remote_file, self.local_file)
        else:
            self.local_file = local_file
        self.configure(self.local_file)

    def get(self, section, option):
        """Read an option from a section
        """
        return self.reader.get(section, option)

    def update(self, section, option=None, value=None):
        """Update an option's value.
        The section or option will be added if not available.
        """
        self.reader.set(section, option, value)
        self.save()

    def delete(self, section, option):
        """Delete an option from a section.
        """
        self.reader.remove_option(section, option)
        self.save()

    def save(self):
        """Save the actions
        """
        self.reader.write(self.file_path)

    def rm_remote_file(self):
        """Remove a file in remote server
        """
        self.sftp.remove_file(self.remote_file)

    def put(self):
        """Upload the local file to remote server
        """
        self.sftp.put_file(self.local_file, self.remote_file)

