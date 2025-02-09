# Imports
import sys
import os
import json
import traceback
from datetime import datetime
import logging

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter, ConversationState, MemoryStorage)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bot.bot import Bot
from config import DefaultConfig

#logging.basicConfig(level=logging.DEBUG)  //TODO: Zum debuggen entkommentieren
#logger = logging.getLogger(__name__)  //TODO: Zum debuggen entkommentieren

config = DefaultConfig()

# Create adapter
settings = BotFrameworkAdapterSettings(config.APP_ID, config.APP_PASSWORD)
adapter = BotFrameworkAdapter(settings)

# Load botsettings
botsettings_file_path = os.path.join(os.path.dirname(__file__), "botsettings.json")
try:
    with open(botsettings_file_path, "r") as f:
        botsettings_data = json.load(f)
    treatment_fallback = int(botsettings_data.get("treatment_group_fallback", 1))
except ValueError or json.decoder.JSONDecodeError:
    treatment_fallback = 1

# Catch-all for errors
async def on_error(context: TurnContext, error: Exception):
    logging.error(f"Unhandled error: {error}")
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)


adapter.on_turn_error = on_error

# Create global ConversationState and MemoryStorage
memory = MemoryStorage()
conversation_state = ConversationState(memory)

# Create the Bot
bot = Bot(conversation_state, treatment_fallback)

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=201)


app = web.Application(middlewares=[aiohttp_error_middleware])
app.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    try:
        web.run_app(app, host="0.0.0.0", port=config.PORT)
    except Exception as error:
        logger.error(f"An error occurred while starting the app: {error}")
        raise error
