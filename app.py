# Imports
import sys
import os
from dotenv import load_dotenv
import json
import traceback
from datetime import datetime
import logging

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter, ConversationState, MemoryStorage)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

import asyncio
from typing import Dict
from azure.cosmos.exceptions import CosmosAccessConditionFailedError
from botbuilder.azure import CosmosDbPartitionedStorage, CosmosDbPartitionedConfig

from bot.bot import Bot
from config import DefaultConfig


class RetryCosmosDbPartitionedStorage(CosmosDbPartitionedStorage):
    """
    Extension of the Botbuilder Storage, which undertakes automatic retries 
    at PreconditionFailed errors with the database. 
    """

    def __init__(
        self,
        config: CosmosDbPartitionedConfig,
        max_retries: int = 3,
        retry_delay: float = 0.5
    ):
        """
        Constructor of the RetryCosmosDbPartitionedStorage class. Inherits from
        the CosmosDbPartitionedStorage class.

        Args: 
            config (CosmosDbPartitionedConfig): The config class instance for 
            the cosmos db database.
            max_retries (int): The maximum number of retries when an error 
            with the internal database occurs.
            retry_delay (float): The delay before a new retry of the database
            operation.
        """

        super().__init__(config)
        self.max_retries = max_retries 
        self.retry_delay = retry_delay 

    async def write(self, changes: Dict[str, object]):
        """
        Overwrites the write method of the parent class 
        CosmosDbPartitionedStorage to retry failed database operations.

        This method attempts to write a set of changes to the Cosmos DB
        partitioned storage. If a write operation fails due to a 
        PreconditionFailed (i.e., a concurrency conflict), it will 
        automatically retry the operation up to the maximum number of retries 
        specified in the constructor.

        Args: 
            changes (Dict[str, object]): A dictionary of key-value pairs 
            representing items to be written to the storage. 
        """
        
        attempt = 0
        while True:
            try:
                # Invoke the orignial implementation from 
                # CosmosDbPartitionedStorage
                return await super().write(changes)
            except CosmosAccessConditionFailedError as e:
                attempt += 1
                if attempt >= self.max_retries:
                    # If all retries are exhausted, pass on the error
                    raise e
                # Wait a short time an try the databse operation again
                await asyncio.sleep(self.retry_delay)


#logging.basicConfig(level=logging.DEBUG)  //TODO: Zum debuggen entkommentieren
#logger = logging.getLogger(__name__)  //TODO: Zum debuggen entkommentieren

config = DefaultConfig()

# Load environment variables
load_dotenv()

# Create adapter
settings = BotFrameworkAdapterSettings(config.APP_ID, config.APP_PASSWORD)
adapter = BotFrameworkAdapter(settings)

# Load botsettings
botsettings_file_path = os.path.join(os.path.dirname(__file__), "botsettings.json")
try:
    with open(botsettings_file_path, "r", encoding="utf-8") as f:
        botsettings_data = json.load(f)
    treatment_fallback = int(botsettings_data.get("treatment_group_fallback", 1))
    use_cosmos_db_storage = bool(botsettings_data.get("use_cosmos_db_storage", False))
except (ValueError, json.decoder.JSONDecodeError):
    treatment_fallback = 1
    use_cosmos_db_storage = False

# Catch-all for errors
async def on_error(context: TurnContext, error: Exception):
    logging.error(f"Unhandled error: {error}")
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()
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

# Create global ConversationState and Storage
if use_cosmos_db_storage == True: 
    cosmos_db_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    auth_key = os.getenv("COSMOS_DB_AUTH_KEY")
    database_id = os.getenv("COSMOS_DB_DATABASE_ID")
    container_id = os.getenv("COSMOS_DB_CONTAINER_ID")
    cosmos_config = CosmosDbPartitionedConfig(
        cosmos_db_endpoint=cosmos_db_endpoint,
        auth_key=auth_key,
        database_id=database_id,
        container_id=container_id,
        container_throughput=None    # to make it compatible with the serverless cosmosdb. 
    )
    storage = RetryCosmosDbPartitionedStorage(
        config=cosmos_config,
        max_retries=3,
        retry_delay=0.5
    )
    conversation_state = ConversationState(storage)
else:
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
        #logger.error(f"An error occurred while starting the app: {error}")
        raise error
