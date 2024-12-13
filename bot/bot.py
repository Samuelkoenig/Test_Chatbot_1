from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ChannelAccount


class Bot(ActivityHandler):

    def __init__(self, conversation_state: ConversationState):
        self.conversation_state = conversation_state
        self.welcome_state_accessor = self.conversation_state.create_property("WelcomeState")

    async def on_message_activity(self, turn_context: TurnContext):
        await turn_context.send_activity(f"You said '{ turn_context.activity.text }'")

    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        welcome_sent = await self.welcome_state_accessor.get(turn_context, False)
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id and not welcome_sent:
                await turn_context.send_activity("Wilkommen! Womit kann ich helfen?")
                await self.welcome_state_accessor.set(turn_context, True)
                await self.conversation_state.save_changes(turn_context)
