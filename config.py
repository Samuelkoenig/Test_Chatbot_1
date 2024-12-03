import os

class DefaultConfig:
    """ Bot Configuration """

    port = int(os.environ.get("PORT", 3978))
    app_id = os.environ.get("MicrosoftAppId", "")
    app_password = os.environ.get("MicrosoftAppPassword", "")
