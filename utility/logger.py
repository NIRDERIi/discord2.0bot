import datetime

class Log:

    def __init__(self, file_to_write: str='logs.log'):
        self.file_to_write = file_to_write

    def get_logger(self, extension_file: str):
        return FileLogger(file=self.file_to_write, extension_file=extension_file)


class FileLogger:

    def __init__(self, file: str, extension_file: str):
        self.file = file
        self.extension_file = extension_file

    def info(self, message: str):
        format_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{format_time} :{self.extension_file}: :INFO: {message}\n'
        with open(self.file, 'a+', encoding='utf-8') as file:
            file.write(text)
        pass

    def warn(self, message: str):
        format_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{format_time} :{self.extension_file}: :WARN: {message}\n'
        with open(self.file, 'a+', encoding='utf-8') as file:
            file.write(text)
        pass

    def debug(self, message: str):
        format_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{format_time} :{self.extension_file}: :DEBUG: {message}\n'
        with open(self.file, 'a+', encoding='utf-8') as file:
            file.write(text)
        pass

    def error(self, message: str):
        format_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{format_time} :{self.extension_file}: :ERROR: {message}\n'
        with open(self.file, 'a+', encoding='utf-8') as file:
            file.write(text)
        pass

    def cog(self, message: str):
        format_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        text = f'{format_time} :{self.extension_file}: :EXTENSION\COG ACTION: {message}\n'
        with open(self.file, 'a+', encoding='utf-8') as file:
            file.write(text)
        pass