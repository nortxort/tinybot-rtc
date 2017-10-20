

class CheckUser:
    """
    A class to perform various ban checks on a User object.

    The checks will be done, against the different ban lists
    and other ban rules in the config file.

    If a test is True, then the user will be banned.
    As default moderator accounts and nicks are not checked.
    """
    def __init__(self, tinybot, user, conf):
        """
        Initialize the CheckUser class.

        :param tinybot: An instance of TinychatBot.
        :type tinybot: TinychatBot
        :param user: The User object to check.
        :type user: User
        :param conf: The config file.
        :type conf: config
        """
        self.tinybot = tinybot
        self.user = user
        self.config = conf

    def check_account(self):
        """
        Check if the user account is in the account bans list.

        :return: True, if the user was banned.
        :rtype: bool
        """
        if self.user.account in self.config.B_ACCOUNT_BANS:

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_kick_msg(self.user.id)
            else:
                self.tinybot.send_ban_msg(self.user.id)

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_chat_msg('Auto-Kicked: (bad account)')
            else:
                self.tinybot.send_chat_msg('Auto-Banned: (bad account)')

            return True

        return False

    def guest_entry(self):
        """
        Check if the user is a guest, and allowed to join.

        :return: True, if the user was banned.
        :rtype: bool
        """
        if self.user.account == '' and not self.config.B_ALLOW_GUESTS:

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_kick_msg(self.user.id)
            else:
                self.tinybot.send_ban_msg(self.user.id)

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_chat_msg('Auto-Kicked: (guests not allowed)')
            else:
                self.tinybot.send_chat_msg('Auto-Banned: (guests not allowed)')

            return True

        return False

    def check_nick(self):
        """
        Check if the user's nick is in the nick bans list.

        :return: True, if the user was banned.
        :rtype: bool
        """
        if self.user.nick in self.config.B_NICK_BANS:

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_kick_msg(self.user.id)
            else:
                self.tinybot.send_ban_msg(self.user.id)

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_chat_msg('Auto-Kicked: (bad nick)')
            else:
                self.tinybot.send_chat_msg('Auto-Banned: (bad nick)')

            return True

        return False

    def check_lurker(self):
        """
        Check if the user is a lurker, and allowed to join.

        :return: True, if the user was banned.
        :rtype: bool
        """
        if self.user.is_lurker and not self.config.B_ALLOW_LURKERS:

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_kick_msg(self.user.id)
            else:
                self.tinybot.send_ban_msg(self.user.id)

            if self.config.B_USE_KICK_AS_AUTOBAN:
                self.tinybot.send_chat_msg('Auto-Kicked: (lurkers not allowed)')
            else:
                self.tinybot.send_chat_msg('Auto-Banned: (lurkers not allowed)')

            return True

        return False
