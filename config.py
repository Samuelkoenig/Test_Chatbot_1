import os

class DefaultConfig:
    """ Bot Configuration """

    port = 3978
    app_id = os.environ.get("MicrosoftAppId", "")
    app_password = os.environ.get("MicrosoftAppPassword", "")
