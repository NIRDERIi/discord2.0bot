class Emojis:
    @staticmethod
    def custom_approval():
        return "<:box_check_mark:865121266969477120>"

    @staticmethod
    def custom_denial():
        return "<:X_:864991033914163239>"

    @staticmethod
    def double_left_arrows():
        return "<:double_left_arrows:864844981369700364>"

    @staticmethod
    def double_right_arrows():
        return "<:double_right_arrows:864844402627575808>"

    @staticmethod
    def right_arrow():
        return "<:right_arrow:864597473347764228>"

    @staticmethod
    def left_arrow():
        return "<:left_arrow:864772067350020106>"

    @staticmethod
    def garbage():
        return "<:trash:864773116794503178>"

    @staticmethod
    def recycle():
        return "<:restart:869949734293475348>"

    @staticmethod
    def lock():
        return "<:lock:864989615256502313>"


class Time:
    @staticmethod
    def BASIC_TIMEOUT():

        return 20.0

    @staticmethod
    def BASIC_DBS_TIMEOUT():

        return 30.0


class Messages:
    @staticmethod
    def BASIC_UNAUTHORIZED_MESSAGE():
        return "You are not authorized to use this command."

    @staticmethod
    def UNKNOWN_EXTENSION():
        return "This extension was not found."

    @staticmethod
    def UNKNOWN_SELFLIB():
        return "`{}` self-lib was not found."


class General:
    @staticmethod
    def REPO_LINK():
        return "https://github.com/NIRDERIi/discord2.0bot"

    @staticmethod
    def GIT_REPO_LINK():
        return "https://github.com/NIRDERIi/discord2.0bot.git"

    @staticmethod
    def SUPPORT_SERVER():
        return "https://discord.gg/htTeS6qfNg"

    @staticmethod
    def GITHUB_IMAGE():
        return "https://avatars.githubusercontent.com/u/9919?s=200&v=4"

    @staticmethod
    def PYPI_IMAGE():
        return 'https://cdn.discordapp.com/emojis/876566097111974009.png?v=1'
